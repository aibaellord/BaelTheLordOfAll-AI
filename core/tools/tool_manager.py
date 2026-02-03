#!/usr/bin/env python3
"""
BAEL - Tool Manager
Advanced tool orchestration for AI agent operations.

Features:
- Tool registration and discovery
- Tool execution
- Parameter validation
- Tool composition
- Parallel tool execution
- Tool authorization
- Usage tracking
- Tool schemas
"""

import asyncio
import copy
import hashlib
import inspect
import json
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union, get_type_hints)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ToolCategory(Enum):
    """Tool categories."""
    SEARCH = "search"
    CODE = "code"
    FILE = "file"
    WEB = "web"
    DATA = "data"
    SYSTEM = "system"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """Tool status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    BETA = "beta"


class ParameterType(Enum):
    """Parameter types."""
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


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    param_type: ParameterType
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None


@dataclass
class ToolSchema:
    """Tool schema definition."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """Complete tool definition."""
    tool_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.CUSTOM
    status: ToolStatus = ToolStatus.ACTIVE
    schema: Optional[ToolSchema] = None
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    requires_auth: bool = False
    timeout: float = 30.0
    max_retries: int = 0
    rate_limit: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Tool execution result."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolUsage:
    """Tool usage record."""
    usage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    user_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None


@dataclass
class ToolStats:
    """Tool statistics."""
    total_calls: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration: float = 0.0
    last_used: Optional[datetime] = None


# =============================================================================
# TOOL BASE
# =============================================================================

class Tool(ABC):
    """Abstract tool base."""

    def __init__(self, definition: ToolDefinition):
        self.definition = definition

    @abstractmethod
    async def execute(
        self,
        **parameters: Any
    ) -> Any:
        """Execute tool."""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate parameters against schema."""
        errors = []

        if not self.definition.schema:
            return errors

        for param in self.definition.schema.parameters:
            value = parameters.get(param.name)

            if value is None:
                if param.required and param.default is None:
                    errors.append(f"Missing required parameter: {param.name}")
                continue

            # Type validation
            if param.param_type == ParameterType.STRING:
                if not isinstance(value, str):
                    errors.append(f"{param.name} must be a string")
            elif param.param_type == ParameterType.INTEGER:
                if not isinstance(value, int):
                    errors.append(f"{param.name} must be an integer")
            elif param.param_type == ParameterType.FLOAT:
                if not isinstance(value, (int, float)):
                    errors.append(f"{param.name} must be a number")
            elif param.param_type == ParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append(f"{param.name} must be a boolean")
            elif param.param_type == ParameterType.ARRAY:
                if not isinstance(value, (list, tuple)):
                    errors.append(f"{param.name} must be an array")
            elif param.param_type == ParameterType.OBJECT:
                if not isinstance(value, dict):
                    errors.append(f"{param.name} must be an object")

            # Enum validation
            if param.enum and value not in param.enum:
                errors.append(f"{param.name} must be one of: {param.enum}")

            # Range validation
            if param.min_value is not None and isinstance(value, (int, float)):
                if value < param.min_value:
                    errors.append(f"{param.name} must be >= {param.min_value}")

            if param.max_value is not None and isinstance(value, (int, float)):
                if value > param.max_value:
                    errors.append(f"{param.name} must be <= {param.max_value}")

        return errors


class FunctionTool(Tool):
    """Tool wrapping a function."""

    def __init__(
        self,
        definition: ToolDefinition,
        func: Callable[..., Any]
    ):
        super().__init__(definition)
        self._func = func
        self._is_async = asyncio.iscoroutinefunction(func)

    async def execute(self, **parameters: Any) -> Any:
        """Execute function."""
        if self._is_async:
            return await self._func(**parameters)
        else:
            return self._func(**parameters)


class LambdaTool(Tool):
    """Quick tool from lambda."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any]
    ):
        definition = ToolDefinition(
            name=name,
            description=description
        )
        super().__init__(definition)
        self._func = func
        self._is_async = asyncio.iscoroutinefunction(func)

    async def execute(self, **parameters: Any) -> Any:
        """Execute lambda."""
        if self._is_async:
            return await self._func(**parameters)
        else:
            return self._func(**parameters)


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """Registry for tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._by_category: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)

    def register(self, tool: Tool) -> str:
        """Register tool."""
        name = tool.definition.name
        self._tools[name] = tool
        self._by_category[tool.definition.category].append(name)

        for tag in tool.definition.tags:
            self._by_tag[tag].append(name)

        return name

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)

    def unregister(self, name: str) -> bool:
        """Unregister tool."""
        tool = self._tools.pop(name, None)
        if tool:
            if name in self._by_category[tool.definition.category]:
                self._by_category[tool.definition.category].remove(name)
            for tag in tool.definition.tags:
                if name in self._by_tag[tag]:
                    self._by_tag[tag].remove(name)
            return True
        return False

    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get tools by category."""
        names = self._by_category.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def get_by_tag(self, tag: str) -> List[Tool]:
        """Get tools by tag."""
        names = self._by_tag.get(tag, [])
        return [self._tools[n] for n in names if n in self._tools]

    def search(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None
    ) -> List[Tool]:
        """Search tools."""
        results = []
        query_lower = query.lower()

        for tool in self._tools.values():
            if category and tool.definition.category != category:
                continue

            if status and tool.definition.status != status:
                continue

            # Search in name and description
            if (query_lower in tool.definition.name.lower() or
                query_lower in tool.definition.description.lower()):
                results.append(tool)

        return results

    def list_all(self) -> List[Tool]:
        """List all tools."""
        return list(self._tools.values())


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

class ToolExecutor:
    """Execute tools with error handling."""

    def __init__(self):
        self._rate_limits: Dict[str, List[datetime]] = defaultdict(list)

    async def execute(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        validate: bool = True
    ) -> ToolResult:
        """Execute tool."""
        start_time = time.time()
        tool_name = tool.definition.name

        try:
            # Validate parameters
            if validate:
                errors = tool.validate_parameters(parameters)
                if errors:
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error="; ".join(errors),
                        duration=time.time() - start_time
                    )

            # Check rate limit
            if tool.definition.rate_limit:
                if not self._check_rate_limit(tool_name, tool.definition.rate_limit):
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error="Rate limit exceeded",
                        duration=time.time() - start_time
                    )

            # Execute with timeout
            result = await asyncio.wait_for(
                tool.execute(**parameters),
                timeout=tool.definition.timeout
            )

            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                duration=time.time() - start_time
            )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool execution timed out",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )

    async def execute_parallel(
        self,
        tools_and_params: List[Tuple[Tool, Dict[str, Any]]]
    ) -> List[ToolResult]:
        """Execute multiple tools in parallel."""
        tasks = []
        for tool, params in tools_and_params:
            task = asyncio.create_task(self.execute(tool, params))
            tasks.append(task)

        return await asyncio.gather(*tasks)

    def _check_rate_limit(self, tool_name: str, limit: int) -> bool:
        """Check rate limit."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old entries
        self._rate_limits[tool_name] = [
            t for t in self._rate_limits[tool_name]
            if t > minute_ago
        ]

        if len(self._rate_limits[tool_name]) >= limit:
            return False

        self._rate_limits[tool_name].append(now)
        return True


# =============================================================================
# TOOL COMPOSER
# =============================================================================

class ToolComposer:
    """Compose multiple tools."""

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def sequence(
        self,
        name: str,
        tool_names: List[str],
        mappings: Optional[List[Dict[str, str]]] = None
    ) -> Tool:
        """Create sequential tool composition."""
        tools = []
        for tname in tool_names:
            tool = self._registry.get(tname)
            if tool:
                tools.append(tool)

        return SequentialTool(name, tools, mappings or [])

    def parallel(
        self,
        name: str,
        tool_names: List[str]
    ) -> Tool:
        """Create parallel tool composition."""
        tools = []
        for tname in tool_names:
            tool = self._registry.get(tname)
            if tool:
                tools.append(tool)

        return ParallelTool(name, tools)

    def conditional(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], str],
        branches: Dict[str, str]
    ) -> Tool:
        """Create conditional tool."""
        branch_tools = {}
        for branch_name, tool_name in branches.items():
            tool = self._registry.get(tool_name)
            if tool:
                branch_tools[branch_name] = tool

        return ConditionalTool(name, condition, branch_tools)


class SequentialTool(Tool):
    """Sequential tool composition."""

    def __init__(
        self,
        name: str,
        tools: List[Tool],
        mappings: List[Dict[str, str]]
    ):
        definition = ToolDefinition(
            name=name,
            description=f"Sequential: {', '.join(t.definition.name for t in tools)}"
        )
        super().__init__(definition)
        self._tools = tools
        self._mappings = mappings

    async def execute(self, **parameters: Any) -> Any:
        """Execute tools in sequence."""
        current_params = parameters.copy()
        result = None

        for i, tool in enumerate(self._tools):
            result = await tool.execute(**current_params)

            # Apply mapping for next tool
            if i < len(self._mappings):
                mapping = self._mappings[i]
                for target, source in mapping.items():
                    if source == "$result":
                        current_params[target] = result
                    elif source.startswith("$result."):
                        key = source[8:]
                        if isinstance(result, dict):
                            current_params[target] = result.get(key)

        return result


class ParallelTool(Tool):
    """Parallel tool composition."""

    def __init__(self, name: str, tools: List[Tool]):
        definition = ToolDefinition(
            name=name,
            description=f"Parallel: {', '.join(t.definition.name for t in tools)}"
        )
        super().__init__(definition)
        self._tools = tools

    async def execute(self, **parameters: Any) -> Dict[str, Any]:
        """Execute tools in parallel."""
        tasks = []
        for tool in self._tools:
            task = asyncio.create_task(tool.execute(**parameters))
            tasks.append((tool.definition.name, task))

        results = {}
        for name, task in tasks:
            results[name] = await task

        return results


class ConditionalTool(Tool):
    """Conditional tool execution."""

    def __init__(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], str],
        branches: Dict[str, Tool]
    ):
        definition = ToolDefinition(
            name=name,
            description=f"Conditional: {list(branches.keys())}"
        )
        super().__init__(definition)
        self._condition = condition
        self._branches = branches

    async def execute(self, **parameters: Any) -> Any:
        """Execute matching branch."""
        branch_name = self._condition(parameters)

        if branch_name not in self._branches:
            raise ValueError(f"Unknown branch: {branch_name}")

        tool = self._branches[branch_name]
        return await tool.execute(**parameters)


# =============================================================================
# USAGE TRACKER
# =============================================================================

class ToolUsageTracker:
    """Track tool usage."""

    def __init__(self):
        self._usage: List[ToolUsage] = []
        self._stats: Dict[str, ToolStats] = defaultdict(ToolStats)

    def record(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        success: bool,
        duration: float,
        error: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ToolUsage:
        """Record usage."""
        usage = ToolUsage(
            tool_name=tool_name,
            user_id=user_id,
            parameters=parameters,
            success=success,
            duration=duration,
            error=error
        )

        self._usage.append(usage)

        # Update stats
        stats = self._stats[tool_name]
        stats.total_calls += 1
        if success:
            stats.successful += 1
            stats.avg_duration = (
                (stats.avg_duration * (stats.successful - 1) + duration) /
                stats.successful
            )
        else:
            stats.failed += 1
        stats.last_used = usage.timestamp

        return usage

    def get_stats(self, tool_name: str) -> ToolStats:
        """Get tool stats."""
        return self._stats.get(tool_name, ToolStats())

    def get_recent_usage(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolUsage]:
        """Get recent usage."""
        usage = self._usage
        if tool_name:
            usage = [u for u in usage if u.tool_name == tool_name]

        return usage[-limit:]

    def get_all_stats(self) -> Dict[str, ToolStats]:
        """Get all stats."""
        return dict(self._stats)


# =============================================================================
# TOOL MANAGER
# =============================================================================

class ToolManager:
    """
    Tool Manager for BAEL.

    Advanced tool orchestration for AI agents.
    """

    def __init__(self):
        self._registry = ToolRegistry()
        self._executor = ToolExecutor()
        self._composer = ToolComposer(self._registry)
        self._tracker = ToolUsageTracker()

    # -------------------------------------------------------------------------
    # REGISTRATION
    # -------------------------------------------------------------------------

    def register(self, tool: Tool) -> str:
        """Register tool."""
        return self._registry.register(tool)

    def register_function(
        self,
        name: str,
        func: Callable[..., Any],
        description: str = "",
        category: ToolCategory = ToolCategory.CUSTOM,
        tags: Optional[List[str]] = None,
        timeout: float = 30.0
    ) -> str:
        """Register function as tool."""
        # Build schema from function signature
        params = []
        sig = inspect.signature(func)

        for param_name, param in sig.parameters.items():
            param_type = ParameterType.ANY

            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_type = ParameterType.STRING
                elif param.annotation == int:
                    param_type = ParameterType.INTEGER
                elif param.annotation == float:
                    param_type = ParameterType.FLOAT
                elif param.annotation == bool:
                    param_type = ParameterType.BOOLEAN
                elif param.annotation == list:
                    param_type = ParameterType.ARRAY
                elif param.annotation == dict:
                    param_type = ParameterType.OBJECT

            required = param.default == inspect.Parameter.empty
            default = None if required else param.default

            params.append(ToolParameter(
                name=param_name,
                param_type=param_type,
                required=required,
                default=default
            ))

        schema = ToolSchema(
            name=name,
            description=description,
            parameters=params
        )

        definition = ToolDefinition(
            name=name,
            description=description,
            category=category,
            schema=schema,
            tags=tags or [],
            timeout=timeout
        )

        tool = FunctionTool(definition, func)
        return self._registry.register(tool)

    def register_lambda(
        self,
        name: str,
        description: str,
        func: Callable[..., Any]
    ) -> str:
        """Register lambda as tool."""
        tool = LambdaTool(name, description, func)
        return self._registry.register(tool)

    def unregister(self, name: str) -> bool:
        """Unregister tool."""
        return self._registry.unregister(name)

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._registry.get(name)

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        name: str,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> ToolResult:
        """Execute tool."""
        tool = self._registry.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool not found: {name}"
            )

        params = parameters or {}
        result = await self._executor.execute(tool, params)

        # Track usage
        self._tracker.record(
            tool_name=name,
            parameters=params,
            success=result.success,
            duration=result.duration,
            error=result.error,
            user_id=user_id
        )

        return result

    async def execute_many(
        self,
        calls: List[Tuple[str, Dict[str, Any]]]
    ) -> List[ToolResult]:
        """Execute multiple tools."""
        tools_and_params = []

        for name, params in calls:
            tool = self._registry.get(name)
            if tool:
                tools_and_params.append((tool, params))

        return await self._executor.execute_parallel(tools_and_params)

    # -------------------------------------------------------------------------
    # COMPOSITION
    # -------------------------------------------------------------------------

    def compose_sequence(
        self,
        name: str,
        tool_names: List[str],
        mappings: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Create sequential tool."""
        tool = self._composer.sequence(name, tool_names, mappings)
        return self._registry.register(tool)

    def compose_parallel(
        self,
        name: str,
        tool_names: List[str]
    ) -> str:
        """Create parallel tool."""
        tool = self._composer.parallel(name, tool_names)
        return self._registry.register(tool)

    def compose_conditional(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], str],
        branches: Dict[str, str]
    ) -> str:
        """Create conditional tool."""
        tool = self._composer.conditional(name, condition, branches)
        return self._registry.register(tool)

    # -------------------------------------------------------------------------
    # DISCOVERY
    # -------------------------------------------------------------------------

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None
    ) -> List[ToolDefinition]:
        """List tools."""
        tools = self._registry.list_all()

        if category:
            tools = [t for t in tools if t.definition.category == category]

        if status:
            tools = [t for t in tools if t.definition.status == status]

        return [t.definition for t in tools]

    def search(
        self,
        query: str,
        category: Optional[ToolCategory] = None
    ) -> List[ToolDefinition]:
        """Search tools."""
        tools = self._registry.search(query, category)
        return [t.definition for t in tools]

    def get_by_tag(self, tag: str) -> List[ToolDefinition]:
        """Get tools by tag."""
        tools = self._registry.get_by_tag(tag)
        return [t.definition for t in tools]

    # -------------------------------------------------------------------------
    # SCHEMA
    # -------------------------------------------------------------------------

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """Get tool schema."""
        tool = self._registry.get(name)
        return tool.definition.schema if tool else None

    def get_openai_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool schema in OpenAI format."""
        tool = self._registry.get(name)
        if not tool or not tool.definition.schema:
            return None

        schema = tool.definition.schema

        properties = {}
        required = []

        for param in schema.parameters:
            prop = {
                "type": param.param_type.value,
                "description": param.description
            }

            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": schema.name,
                "description": schema.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def get_all_openai_schemas(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format."""
        schemas = []

        for tool in self._registry.list_all():
            schema = self.get_openai_schema(tool.definition.name)
            if schema:
                schemas.append(schema)

        return schemas

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self, name: str) -> ToolStats:
        """Get tool stats."""
        return self._tracker.get_stats(name)

    def get_all_stats(self) -> Dict[str, ToolStats]:
        """Get all stats."""
        return self._tracker.get_all_stats()

    def get_recent_usage(
        self,
        name: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolUsage]:
        """Get recent usage."""
        return self._tracker.get_recent_usage(name, limit)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tool Manager."""
    print("=" * 70)
    print("BAEL - TOOL MANAGER DEMO")
    print("Advanced Tool Orchestration for AI Agents")
    print("=" * 70)
    print()

    manager = ToolManager()

    # 1. Register Function Tools
    print("1. REGISTER FUNCTION TOOLS:")
    print("-" * 40)

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

    async def fetch_data(url: str) -> Dict[str, Any]:
        """Fetch data from URL."""
        await asyncio.sleep(0.1)
        return {"url": url, "status": "fetched"}

    manager.register_function(
        name="add",
        func=add,
        description="Add two numbers",
        category=ToolCategory.DATA,
        tags=["math", "calculator"]
    )

    manager.register_function(
        name="multiply",
        func=multiply,
        description="Multiply two numbers",
        category=ToolCategory.DATA,
        tags=["math", "calculator"]
    )

    manager.register_function(
        name="fetch_data",
        func=fetch_data,
        description="Fetch data from URL",
        category=ToolCategory.WEB,
        tags=["http", "api"]
    )

    print("   Registered: add, multiply, fetch_data")
    print()

    # 2. Execute Tools
    print("2. EXECUTE TOOLS:")
    print("-" * 40)

    result = await manager.execute("add", {"a": 5, "b": 3})
    print(f"   add(5, 3) = {result.result}")

    result = await manager.execute("multiply", {"a": 4, "b": 7})
    print(f"   multiply(4, 7) = {result.result}")

    result = await manager.execute("fetch_data", {"url": "https://example.com"})
    print(f"   fetch_data result: {result.result}")
    print()

    # 3. Lambda Tools
    print("3. LAMBDA TOOLS:")
    print("-" * 40)

    manager.register_lambda(
        name="greet",
        description="Greet someone",
        func=lambda name: f"Hello, {name}!"
    )

    result = await manager.execute("greet", {"name": "BAEL"})
    print(f"   greet('BAEL') = {result.result}")
    print()

    # 4. Parameter Validation
    print("4. PARAMETER VALIDATION:")
    print("-" * 40)

    result = await manager.execute("add", {"a": "not_a_number", "b": 3})
    print(f"   Invalid params: {result.error}")

    result = await manager.execute("add", {"a": 5})
    print(f"   Missing param: {result.error}")
    print()

    # 5. Sequential Composition
    print("5. SEQUENTIAL COMPOSITION:")
    print("-" * 40)

    manager.compose_sequence(
        name="add_then_multiply",
        tool_names=["add", "multiply"],
        mappings=[{"a": "$result", "b": "2"}]  # Multiply result by 2
    )

    # Note: This won't work perfectly due to the param structure
    # but demonstrates the concept
    print("   Created: add_then_multiply")
    print()

    # 6. Parallel Composition
    print("6. PARALLEL COMPOSITION:")
    print("-" * 40)

    manager.compose_parallel(
        name="add_and_multiply",
        tool_names=["add", "multiply"]
    )

    result = await manager.execute("add_and_multiply", {"a": 5, "b": 3})
    print(f"   Parallel result: {result.result}")
    print()

    # 7. Conditional Composition
    print("7. CONDITIONAL COMPOSITION:")
    print("-" * 40)

    def choose_operation(params: Dict[str, Any]) -> str:
        return "add" if params.get("operation") == "add" else "multiply"

    manager.compose_conditional(
        name="calculator",
        condition=choose_operation,
        branches={
            "add": "add",
            "multiply": "multiply"
        }
    )

    result = await manager.execute("calculator", {"operation": "add", "a": 10, "b": 5})
    print(f"   calculator(add, 10, 5) = {result.result}")

    result = await manager.execute("calculator", {"operation": "multiply", "a": 10, "b": 5})
    print(f"   calculator(multiply, 10, 5) = {result.result}")
    print()

    # 8. Execute Many
    print("8. EXECUTE MANY:")
    print("-" * 40)

    results = await manager.execute_many([
        ("add", {"a": 1, "b": 2}),
        ("add", {"a": 3, "b": 4}),
        ("multiply", {"a": 5, "b": 6})
    ])

    for r in results:
        print(f"   {r.tool_name}: {r.result}")
    print()

    # 9. Tool Discovery
    print("9. TOOL DISCOVERY:")
    print("-" * 40)

    all_tools = manager.list_tools()
    print(f"   Total tools: {len(all_tools)}")

    data_tools = manager.list_tools(category=ToolCategory.DATA)
    print(f"   Data tools: {len(data_tools)}")

    math_tools = manager.get_by_tag("math")
    print(f"   Math tools: {len(math_tools)}")
    print()

    # 10. Search Tools
    print("10. SEARCH TOOLS:")
    print("-" * 40)

    results = manager.search("add")
    print(f"   Search 'add': {[t.name for t in results]}")

    results = manager.search("multiply")
    print(f"   Search 'multiply': {[t.name for t in results]}")
    print()

    # 11. Tool Schema
    print("11. TOOL SCHEMA:")
    print("-" * 40)

    schema = manager.get_schema("add")
    if schema:
        print(f"   Name: {schema.name}")
        print(f"   Params: {[p.name for p in schema.parameters]}")
    print()

    # 12. OpenAI Schema
    print("12. OPENAI SCHEMA:")
    print("-" * 40)

    openai_schema = manager.get_openai_schema("add")
    if openai_schema:
        print(f"   Type: {openai_schema['type']}")
        print(f"   Function: {openai_schema['function']['name']}")
    print()

    # 13. All OpenAI Schemas
    print("13. ALL OPENAI SCHEMAS:")
    print("-" * 40)

    all_schemas = manager.get_all_openai_schemas()
    print(f"   Total schemas: {len(all_schemas)}")
    for schema in all_schemas[:3]:
        print(f"     - {schema['function']['name']}")
    print()

    # 14. Usage Stats
    print("14. USAGE STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats("add")
    print(f"   Tool: add")
    print(f"   Total calls: {stats.total_calls}")
    print(f"   Successful: {stats.successful}")
    print(f"   Avg duration: {stats.avg_duration:.4f}s")
    print()

    # 15. Recent Usage
    print("15. RECENT USAGE:")
    print("-" * 40)

    usage = manager.get_recent_usage(limit=5)
    print(f"   Recent calls: {len(usage)}")
    for u in usage[:3]:
        print(f"     - {u.tool_name}: success={u.success}")
    print()

    # 16. All Stats
    print("16. ALL TOOL STATS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()
    print(f"   Tools with stats: {len(all_stats)}")
    for name, stats in list(all_stats.items())[:3]:
        print(f"     - {name}: {stats.total_calls} calls")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Tool Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
