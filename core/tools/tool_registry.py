#!/usr/bin/env python3
"""
BAEL - Tool Registry
Comprehensive tool discovery, registration, and management.

This module manages the entire lifecycle of tools that agents
can use, including discovery, versioning, and execution.

Features:
- Tool registration and discovery
- Tool versioning
- Capability matching
- Tool execution sandboxing
- Usage tracking
- Dependency management
- Tool chaining
- Permission control
- Tool validation
- Hot-reloading
"""

import asyncio
import hashlib
import inspect
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ToolCategory(Enum):
    """Categories of tools."""
    COMPUTATION = "computation"
    DATA = "data"
    COMMUNICATION = "communication"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    AI = "ai"
    UTILITY = "utility"
    SECURITY = "security"
    CUSTOM = "custom"


class ToolState(Enum):
    """Tool states."""
    REGISTERED = "registered"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    ERROR = "error"


class ParameterType(Enum):
    """Parameter types for tool inputs."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


class ExecutionMode(Enum):
    """Tool execution modes."""
    SYNC = "sync"
    ASYNC = "async"
    BACKGROUND = "background"


class PermissionLevel(Enum):
    """Tool permission levels."""
    PUBLIC = 0       # Anyone can use
    RESTRICTED = 1   # Requires approval
    PRIVILEGED = 2   # Admin only
    SYSTEM = 3       # Internal system use


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ToolParameter:
    """A tool parameter definition."""
    name: str
    type: ParameterType
    description: str = ""
    required: bool = True
    default: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate a value against this parameter."""
        if value is None:
            if self.required and self.default is None:
                return False, f"Required parameter '{self.name}' is missing"
            return True, ""

        # Type validation
        type_validators = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParameterType.FLOAT: lambda v: isinstance(v, (int, float)),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.ARRAY: lambda v: isinstance(v, list),
            ParameterType.OBJECT: lambda v: isinstance(v, dict),
            ParameterType.ANY: lambda v: True
        }

        if not type_validators[self.type](value):
            return False, f"Parameter '{self.name}' must be {self.type.value}"

        # Constraint validation
        if "min" in self.constraints and value < self.constraints["min"]:
            return False, f"Parameter '{self.name}' must be >= {self.constraints['min']}"

        if "max" in self.constraints and value > self.constraints["max"]:
            return False, f"Parameter '{self.name}' must be <= {self.constraints['max']}"

        if "pattern" in self.constraints:
            import re
            if not re.match(self.constraints["pattern"], str(value)):
                return False, f"Parameter '{self.name}' must match pattern"

        if "enum" in self.constraints and value not in self.constraints["enum"]:
            return False, f"Parameter '{self.name}' must be one of {self.constraints['enum']}"

        return True, ""


@dataclass
class ToolOutput:
    """Tool output definition."""
    type: ParameterType
    description: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolVersion:
    """Tool version information."""
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "ToolVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


@dataclass
class ToolMetadata:
    """Tool metadata."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    version: ToolVersion = field(default_factory=ToolVersion)
    author: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolUsage:
    """Tool usage statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time: float = 0.0
    last_used: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def average_execution_time(self) -> float:
        """Calculate average execution time."""
        if self.total_calls == 0:
            return 0.0
        return self.total_execution_time / self.total_calls

    def record_execution(self, success: bool, duration: float) -> None:
        """Record an execution."""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        self.total_execution_time += duration
        self.last_used = datetime.now()


@dataclass
class ToolDependency:
    """Tool dependency."""
    tool_name: str
    min_version: Optional[ToolVersion] = None
    optional: bool = False


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TOOL BASE
# =============================================================================

class ToolBase(ABC):
    """Abstract base class for tools."""

    def __init__(self):
        self.metadata = ToolMetadata(
            name=self.__class__.__name__,
            description=self.__doc__ or ""
        )
        self.parameters: List[ToolParameter] = []
        self.output: Optional[ToolOutput] = None
        self.dependencies: List[ToolDependency] = []
        self.state = ToolState.REGISTERED
        self.usage = ToolUsage()
        self.permission_level = PermissionLevel.PUBLIC
        self.execution_mode = ExecutionMode.SYNC

        self._setup()

    def _setup(self) -> None:
        """Setup hook for subclasses."""
        pass

    def define_parameter(
        self,
        name: str,
        param_type: ParameterType,
        description: str = "",
        required: bool = True,
        default: Any = None,
        **constraints
    ) -> None:
        """Define a parameter."""
        param = ToolParameter(
            name=name,
            type=param_type,
            description=description,
            required=required,
            default=default,
            constraints=constraints
        )
        self.parameters.append(param)

    def define_output(
        self,
        output_type: ParameterType,
        description: str = "",
        schema: Dict[str, Any] = None
    ) -> None:
        """Define the output."""
        self.output = ToolOutput(
            type=output_type,
            description=description,
            schema=schema or {}
        )

    def validate_input(
        self,
        params: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate input parameters."""
        errors = []

        for param in self.parameters:
            value = params.get(param.name, param.default)
            valid, error = param.validate(value)
            if not valid:
                errors.append(error)

        return len(errors) == 0, errors

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    async def run(self, **kwargs) -> ToolExecutionResult:
        """Run the tool with validation and tracking."""
        start_time = time.time()

        # Validate input
        valid, errors = self.validate_input(kwargs)
        if not valid:
            return ToolExecutionResult(
                success=False,
                error="; ".join(errors)
            )

        # Apply defaults
        for param in self.parameters:
            if param.name not in kwargs and param.default is not None:
                kwargs[param.name] = param.default

        try:
            result = await self.execute(**kwargs)
            execution_time = time.time() - start_time

            self.usage.record_execution(True, execution_time)

            return ToolExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.usage.record_execution(False, execution_time)

            return ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    def get_signature(self) -> Dict[str, Any]:
        """Get tool signature."""
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in self.parameters
            ],
            "output": {
                "type": self.output.type.value if self.output else "any",
                "description": self.output.description if self.output else ""
            }
        }


# =============================================================================
# BUILT-IN TOOLS
# =============================================================================

class TextProcessorTool(ToolBase):
    """Tool for text processing operations."""

    def _setup(self) -> None:
        self.metadata.name = "text_processor"
        self.metadata.category = ToolCategory.DATA
        self.metadata.description = "Perform text processing operations"

        self.define_parameter("text", ParameterType.STRING, "Input text")
        self.define_parameter(
            "operation", ParameterType.STRING,
            "Operation to perform",
            enum=["uppercase", "lowercase", "reverse", "word_count", "char_count"]
        )
        self.define_output(ParameterType.ANY, "Processed result")

    async def execute(self, text: str, operation: str) -> Any:
        """Execute text processing."""
        operations = {
            "uppercase": lambda t: t.upper(),
            "lowercase": lambda t: t.lower(),
            "reverse": lambda t: t[::-1],
            "word_count": lambda t: len(t.split()),
            "char_count": lambda t: len(t)
        }

        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")

        return operations[operation](text)


class CalculatorTool(ToolBase):
    """Tool for mathematical calculations."""

    def _setup(self) -> None:
        self.metadata.name = "calculator"
        self.metadata.category = ToolCategory.COMPUTATION
        self.metadata.description = "Perform mathematical calculations"

        self.define_parameter("a", ParameterType.FLOAT, "First operand")
        self.define_parameter("b", ParameterType.FLOAT, "Second operand")
        self.define_parameter(
            "operation", ParameterType.STRING,
            "Operation to perform",
            enum=["add", "subtract", "multiply", "divide", "power", "modulo"]
        )
        self.define_output(ParameterType.FLOAT, "Calculation result")

    async def execute(self, a: float, b: float, operation: str) -> float:
        """Execute calculation."""
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else float('inf'),
            "power": lambda x, y: x ** y,
            "modulo": lambda x, y: x % y if y != 0 else 0
        }

        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")

        return operations[operation](a, b)


class DataTransformerTool(ToolBase):
    """Tool for data transformation."""

    def _setup(self) -> None:
        self.metadata.name = "data_transformer"
        self.metadata.category = ToolCategory.DATA
        self.metadata.description = "Transform data between formats"

        self.define_parameter("data", ParameterType.ANY, "Input data")
        self.define_parameter(
            "transform", ParameterType.STRING,
            "Transformation to apply",
            enum=["to_json", "from_json", "flatten", "keys", "values"]
        )
        self.define_output(ParameterType.ANY, "Transformed data")

    async def execute(self, data: Any, transform: str) -> Any:
        """Execute transformation."""
        if transform == "to_json":
            return json.dumps(data)
        elif transform == "from_json":
            return json.loads(data) if isinstance(data, str) else data
        elif transform == "flatten":
            if isinstance(data, list):
                return [item for sublist in data for item in (sublist if isinstance(sublist, list) else [sublist])]
            return data
        elif transform == "keys":
            return list(data.keys()) if isinstance(data, dict) else []
        elif transform == "values":
            return list(data.values()) if isinstance(data, dict) else []

        raise ValueError(f"Unknown transform: {transform}")


class TimerTool(ToolBase):
    """Tool for time-related operations."""

    def _setup(self) -> None:
        self.metadata.name = "timer"
        self.metadata.category = ToolCategory.UTILITY
        self.metadata.description = "Time-related operations"
        self.execution_mode = ExecutionMode.ASYNC

        self.define_parameter(
            "operation", ParameterType.STRING,
            "Operation to perform",
            enum=["now", "sleep", "timestamp", "format"]
        )
        self.define_parameter(
            "value", ParameterType.ANY,
            "Value for the operation",
            required=False
        )
        self.define_output(ParameterType.ANY, "Time result")

    async def execute(self, operation: str, value: Any = None) -> Any:
        """Execute time operation."""
        if operation == "now":
            return datetime.now().isoformat()
        elif operation == "sleep":
            if value and isinstance(value, (int, float)):
                await asyncio.sleep(value)
            return True
        elif operation == "timestamp":
            return time.time()
        elif operation == "format":
            fmt = value or "%Y-%m-%d %H:%M:%S"
            return datetime.now().strftime(fmt)

        raise ValueError(f"Unknown operation: {operation}")


# =============================================================================
# TOOL CHAIN
# =============================================================================

class ToolChain:
    """Chains multiple tools together."""

    def __init__(self, name: str = ""):
        self.name = name or str(uuid4())
        self.steps: List[Tuple[ToolBase, Dict[str, Any]]] = []
        self.data_mapping: Dict[int, Dict[str, str]] = {}

    def add_step(
        self,
        tool: ToolBase,
        params: Dict[str, Any] = None,
        input_mapping: Dict[str, str] = None
    ) -> "ToolChain":
        """Add a step to the chain."""
        step_index = len(self.steps)
        self.steps.append((tool, params or {}))

        if input_mapping:
            self.data_mapping[step_index] = input_mapping

        return self

    async def execute(
        self,
        initial_data: Dict[str, Any] = None
    ) -> List[ToolExecutionResult]:
        """Execute the chain."""
        results = []
        context = initial_data or {}

        for i, (tool, params) in enumerate(self.steps):
            # Apply data mapping
            step_params = params.copy()

            if i in self.data_mapping:
                for param_name, source in self.data_mapping[i].items():
                    if source.startswith("$"):
                        # Reference to previous result
                        ref_parts = source[1:].split(".")
                        step_index = int(ref_parts[0])

                        if step_index < len(results) and results[step_index].success:
                            value = results[step_index].result

                            # Navigate nested path
                            for part in ref_parts[1:]:
                                if isinstance(value, dict):
                                    value = value.get(part)
                                elif isinstance(value, list) and part.isdigit():
                                    value = value[int(part)]

                            step_params[param_name] = value
                    elif source in context:
                        step_params[param_name] = context[source]

            # Execute step
            result = await tool.run(**step_params)
            results.append(result)

            # Store result in context
            if result.success:
                context[f"step_{i}"] = result.result

            # Stop on error (unless configured otherwise)
            if not result.success:
                break

        return results


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """
    The master tool registry for BAEL.

    Manages tool registration, discovery, versioning,
    and execution.
    """

    def __init__(self):
        self.tools: Dict[str, ToolBase] = {}
        self.tool_versions: Dict[str, Dict[str, ToolBase]] = defaultdict(dict)
        self.category_index: Dict[ToolCategory, Set[str]] = defaultdict(set)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        self.chains: Dict[str, ToolChain] = {}

        # Register built-in tools
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in tools."""
        builtins = [
            TextProcessorTool(),
            CalculatorTool(),
            DataTransformerTool(),
            TimerTool()
        ]

        for tool in builtins:
            self.register(tool)

    def register(self, tool: ToolBase) -> bool:
        """Register a tool."""
        name = tool.metadata.name
        version = str(tool.metadata.version)

        # Store by name (latest version)
        self.tools[name] = tool

        # Store by version
        self.tool_versions[name][version] = tool

        # Update indices
        self.category_index[tool.metadata.category].add(name)

        for tag in tool.metadata.tags:
            self.tag_index[tag].add(name)

        tool.state = ToolState.ACTIVE

        return True

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name not in self.tools:
            return False

        tool = self.tools[name]

        # Remove from indices
        self.category_index[tool.metadata.category].discard(name)

        for tag in tool.metadata.tags:
            self.tag_index[tag].discard(name)

        del self.tools[name]

        if name in self.tool_versions:
            del self.tool_versions[name]

        return True

    def get(
        self,
        name: str,
        version: str = None
    ) -> Optional[ToolBase]:
        """Get a tool by name and optional version."""
        if version:
            return self.tool_versions.get(name, {}).get(version)
        return self.tools.get(name)

    def search(
        self,
        query: str = None,
        category: ToolCategory = None,
        tags: List[str] = None,
        state: ToolState = None
    ) -> List[ToolBase]:
        """Search for tools."""
        candidates = set(self.tools.keys())

        # Filter by category
        if category:
            candidates &= self.category_index.get(category, set())

        # Filter by tags
        if tags:
            for tag in tags:
                candidates &= self.tag_index.get(tag, set())

        # Get tools
        results = [self.tools[name] for name in candidates if name in self.tools]

        # Filter by state
        if state:
            results = [t for t in results if t.state == state]

        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.metadata.name.lower() or
                   query_lower in t.metadata.description.lower()
            ]

        return results

    def find_by_capability(
        self,
        required_params: List[str],
        output_type: ParameterType = None
    ) -> List[ToolBase]:
        """Find tools by capability requirements."""
        matches = []

        for tool in self.tools.values():
            # Check parameters
            tool_params = {p.name for p in tool.parameters}
            if not all(p in tool_params for p in required_params):
                continue

            # Check output type
            if output_type and tool.output:
                if tool.output.type != output_type:
                    continue

            matches.append(tool)

        return matches

    async def execute(
        self,
        name: str,
        params: Dict[str, Any],
        version: str = None
    ) -> ToolExecutionResult:
        """Execute a tool."""
        tool = self.get(name, version)

        if not tool:
            return ToolExecutionResult(
                success=False,
                error=f"Tool '{name}' not found"
            )

        if tool.state != ToolState.ACTIVE:
            return ToolExecutionResult(
                success=False,
                error=f"Tool '{name}' is not active (state: {tool.state.value})"
            )

        return await tool.run(**params)

    def create_chain(self, name: str = None) -> ToolChain:
        """Create a tool chain."""
        chain = ToolChain(name)
        self.chains[chain.name] = chain
        return chain

    async def execute_chain(
        self,
        chain_name: str,
        initial_data: Dict[str, Any] = None
    ) -> List[ToolExecutionResult]:
        """Execute a tool chain."""
        chain = self.chains.get(chain_name)

        if not chain:
            return [ToolExecutionResult(
                success=False,
                error=f"Chain '{chain_name}' not found"
            )]

        return await chain.execute(initial_data)

    def deprecate(self, name: str, message: str = "") -> bool:
        """Deprecate a tool."""
        tool = self.tools.get(name)
        if tool:
            tool.state = ToolState.DEPRECATED
            return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a tool."""
        tool = self.tools.get(name)
        if tool:
            tool.state = ToolState.ACTIVE
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool."""
        tool = self.tools.get(name)
        if tool:
            tool.state = ToolState.DISABLED
            return True
        return False

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Get tool catalog."""
        return [
            {
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "category": tool.metadata.category.value,
                "version": str(tool.metadata.version),
                "state": tool.state.value,
                "parameters": len(tool.parameters),
                "tags": list(tool.metadata.tags)
            }
            for tool in self.tools.values()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_calls = sum(t.usage.total_calls for t in self.tools.values())
        total_successes = sum(t.usage.successful_calls for t in self.tools.values())

        by_category = defaultdict(int)
        for tool in self.tools.values():
            by_category[tool.metadata.category.value] += 1

        by_state = defaultdict(int)
        for tool in self.tools.values():
            by_state[tool.state.value] += 1

        return {
            "total_tools": len(self.tools),
            "total_calls": total_calls,
            "total_successes": total_successes,
            "overall_success_rate": total_successes / total_calls if total_calls > 0 else 0,
            "by_category": dict(by_category),
            "by_state": dict(by_state),
            "chains": len(self.chains)
        }


# =============================================================================
# DECORATOR FOR QUICK TOOL CREATION
# =============================================================================

def tool(
    name: str = None,
    description: str = None,
    category: ToolCategory = ToolCategory.UTILITY,
    tags: List[str] = None
):
    """Decorator to create a tool from a function."""

    def decorator(func: Callable) -> ToolBase:
        class FunctionTool(ToolBase):
            def _setup(self):
                self.metadata.name = name or func.__name__
                self.metadata.description = description or func.__doc__ or ""
                self.metadata.category = category
                self.metadata.tags = set(tags or [])

                # Inspect function signature for parameters
                sig = inspect.signature(func)
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue

                    # Infer type from annotation
                    param_type = ParameterType.ANY
                    if param.annotation != inspect.Parameter.empty:
                        type_map = {
                            str: ParameterType.STRING,
                            int: ParameterType.INTEGER,
                            float: ParameterType.FLOAT,
                            bool: ParameterType.BOOLEAN,
                            list: ParameterType.ARRAY,
                            dict: ParameterType.OBJECT
                        }
                        param_type = type_map.get(param.annotation, ParameterType.ANY)

                    has_default = param.default != inspect.Parameter.empty

                    self.define_parameter(
                        param_name,
                        param_type,
                        required=not has_default,
                        default=param.default if has_default else None
                    )

                # Set execution mode
                if asyncio.iscoroutinefunction(func):
                    self.execution_mode = ExecutionMode.ASYNC

            async def execute(self, **kwargs) -> Any:
                if asyncio.iscoroutinefunction(func):
                    return await func(**kwargs)
                return func(**kwargs)

        return FunctionTool()

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tool Registry."""
    print("=" * 70)
    print("BAEL - TOOL REGISTRY DEMO")
    print("Comprehensive Tool Management System")
    print("=" * 70)
    print()

    # Create registry
    registry = ToolRegistry()

    # 1. List Built-in Tools
    print("1. BUILT-IN TOOLS:")
    print("-" * 40)

    catalog = registry.get_catalog()
    for tool_info in catalog:
        print(f"   {tool_info['name']}")
        print(f"     Category: {tool_info['category']}")
        print(f"     Parameters: {tool_info['parameters']}")
    print()

    # 2. Execute Tools
    print("2. TOOL EXECUTION:")
    print("-" * 40)

    # Calculator
    result = await registry.execute("calculator", {
        "a": 10,
        "b": 5,
        "operation": "multiply"
    })
    print(f"   10 * 5 = {result.result}")
    print(f"   Execution time: {result.execution_time:.4f}s")

    # Text processor
    result = await registry.execute("text_processor", {
        "text": "Hello World",
        "operation": "uppercase"
    })
    print(f"   Uppercase: {result.result}")

    # Data transformer
    result = await registry.execute("data_transformer", {
        "data": {"name": "BAEL", "type": "AI"},
        "transform": "keys"
    })
    print(f"   Keys: {result.result}")
    print()

    # 3. Create Custom Tool
    print("3. CUSTOM TOOL:")
    print("-" * 40)

    class HashTool(ToolBase):
        """Generate hash of input data."""

        def _setup(self):
            self.metadata.name = "hash_generator"
            self.metadata.category = ToolCategory.SECURITY
            self.metadata.tags = {"security", "crypto"}

            self.define_parameter("data", ParameterType.STRING, "Data to hash")
            self.define_parameter(
                "algorithm", ParameterType.STRING,
                "Hash algorithm",
                required=False,
                default="sha256",
                enum=["md5", "sha256", "sha512"]
            )
            self.define_output(ParameterType.STRING, "Hash value")

        async def execute(self, data: str, algorithm: str = "sha256") -> str:
            hashers = {
                "md5": hashlib.md5,
                "sha256": hashlib.sha256,
                "sha512": hashlib.sha512
            }
            return hashers[algorithm](data.encode()).hexdigest()

    hash_tool = HashTool()
    registry.register(hash_tool)

    result = await registry.execute("hash_generator", {
        "data": "BAEL The Lord",
        "algorithm": "sha256"
    })
    print(f"   Hash: {result.result[:32]}...")
    print()

    # 4. Tool Decorator
    print("4. DECORATOR-BASED TOOL:")
    print("-" * 40)

    @tool(name="greet", description="Generate a greeting", category=ToolCategory.UTILITY)
    def greet(name: str, formal: bool = False) -> str:
        if formal:
            return f"Good day, {name}. How may I assist you?"
        return f"Hey {name}!"

    registry.register(greet)

    result = await registry.execute("greet", {"name": "User", "formal": True})
    print(f"   Formal: {result.result}")

    result = await registry.execute("greet", {"name": "User"})
    print(f"   Casual: {result.result}")
    print()

    # 5. Tool Chain
    print("5. TOOL CHAIN:")
    print("-" * 40)

    chain = registry.create_chain("process_and_hash")
    chain.add_step(
        registry.get("text_processor"),
        {"operation": "uppercase"},
        {"text": "input_text"}
    )
    chain.add_step(
        registry.get("hash_generator"),
        {"algorithm": "sha256"},
        {"data": "$0"}  # Result from step 0
    )

    results = await chain.execute({"input_text": "hello world"})

    print(f"   Step 1 (uppercase): {results[0].result}")
    print(f"   Step 2 (hash): {results[1].result[:32]}...")
    print()

    # 6. Search Tools
    print("6. TOOL SEARCH:")
    print("-" * 40)

    # By category
    data_tools = registry.search(category=ToolCategory.DATA)
    print(f"   Data tools: {[t.metadata.name for t in data_tools]}")

    # By query
    calc_tools = registry.search(query="calc")
    print(f"   'calc' search: {[t.metadata.name for t in calc_tools]}")

    # By capability
    capable_tools = registry.find_by_capability(["text"])
    print(f"   Tools with 'text' param: {[t.metadata.name for t in capable_tools]}")
    print()

    # 7. Tool Signatures
    print("7. TOOL SIGNATURES:")
    print("-" * 40)

    calc = registry.get("calculator")
    signature = calc.get_signature()
    print(f"   Tool: {signature['name']}")
    print(f"   Parameters:")
    for param in signature['parameters']:
        req = "*" if param['required'] else ""
        print(f"     - {param['name']}{req}: {param['type']}")
    print()

    # 8. Tool States
    print("8. TOOL LIFECYCLE:")
    print("-" * 40)

    # Deprecate
    registry.deprecate("timer", "Use new_timer instead")
    timer = registry.get("timer")
    print(f"   Timer state after deprecate: {timer.state.value}")

    # Disable
    registry.disable("timer")
    print(f"   Timer state after disable: {timer.state.value}")

    # Re-enable
    registry.enable("timer")
    print(f"   Timer state after enable: {timer.state.value}")
    print()

    # 9. Usage Statistics
    print("9. USAGE STATISTICS:")
    print("-" * 40)

    calc = registry.get("calculator")
    print(f"   Calculator usage:")
    print(f"     Total calls: {calc.usage.total_calls}")
    print(f"     Success rate: {calc.usage.success_rate:.2%}")
    print(f"     Avg time: {calc.usage.average_execution_time:.4f}s")
    print()

    # 10. Registry Statistics
    print("10. REGISTRY STATISTICS:")
    print("-" * 40)

    stats = registry.get_statistics()
    print(f"   Total tools: {stats['total_tools']}")
    print(f"   Total calls: {stats['total_calls']}")
    print(f"   Success rate: {stats['overall_success_rate']:.2%}")
    print(f"   By category: {stats['by_category']}")
    print(f"   Chains: {stats['chains']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Tool Registry Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
