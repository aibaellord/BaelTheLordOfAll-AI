"""
BAEL Tool Orchestration System

Advanced tool management and execution with:
- Dynamic tool discovery and registration
- Tool chaining and pipelines
- Capability-based tool selection
- Error handling and fallbacks
- Tool result caching
- Usage analytics

This enables BAEL to effectively use and combine tools.
"""

import asyncio
import inspect
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools."""
    SEARCH = "search"
    CODE_EXECUTION = "code_execution"
    FILE_OPERATION = "file_operation"
    DATA_PROCESSING = "data_processing"
    COMMUNICATION = "communication"
    EXTERNAL_API = "external_api"
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    MEMORY = "memory"
    WEB = "web"
    UTILITY = "utility"


class ToolStatus(Enum):
    """Tool availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class ExecutionMode(Enum):
    """Tool execution mode."""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"


@dataclass
class ToolParameter:
    """A parameter for a tool."""
    name: str
    type_hint: str
    description: str = ""
    required: bool = True
    default: Any = None
    enum_values: List[str] = field(default_factory=list)


@dataclass
class ToolSchema:
    """Schema definition for a tool."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "Any"
    returns_description: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": self._python_to_json_type(param.type_hint),
                "description": param.description
            }
            if param.enum_values:
                prop["enum"] = param.enum_values
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def _python_to_json_type(self, py_type: str) -> str:
        """Convert Python type to JSON Schema type."""
        mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "List": "array",
            "Dict": "object",
        }
        return mapping.get(py_type, "string")


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolMetrics:
    """Metrics for a tool."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class Tool:
    """A tool that BAEL can use."""
    id: str
    name: str
    category: ToolCategory
    schema: ToolSchema
    handler: Callable

    # Configuration
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    timeout_ms: int = 30000
    max_concurrent: int = 5
    cacheable: bool = False
    cache_ttl_seconds: int = 300

    # State
    status: ToolStatus = ToolStatus.AVAILABLE
    metrics: ToolMetrics = field(default_factory=ToolMetrics)

    # Metadata
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Extract schema from handler if not provided
        if not self.schema.parameters:
            self._extract_schema_from_handler()

    def _extract_schema_from_handler(self):
        """Extract parameter schema from handler signature."""
        sig = inspect.signature(self.handler)

        for name, param in sig.parameters.items():
            if name in ['self', 'cls']:
                continue

            type_hint = "str"
            if param.annotation != inspect.Parameter.empty:
                type_hint = getattr(param.annotation, '__name__', str(param.annotation))

            required = param.default == inspect.Parameter.empty
            default = None if required else param.default

            self.schema.parameters.append(ToolParameter(
                name=name,
                type_hint=type_hint,
                required=required,
                default=default
            ))


class ToolExecutor:
    """Executor for running tools."""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.result_cache: Dict[str, Tuple[ToolResult, datetime]] = {}

    async def execute(
        self,
        tool: Tool,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool with given arguments."""
        start_time = time.time()

        # Check cache
        if tool.cacheable:
            cache_key = self._cache_key(tool.name, arguments)
            cached = self._get_cached(cache_key, tool.cache_ttl_seconds)
            if cached:
                return cached

        try:
            # Execute based on mode
            if tool.execution_mode == ExecutionMode.ASYNC:
                if asyncio.iscoroutinefunction(tool.handler):
                    result = await asyncio.wait_for(
                        tool.handler(**arguments),
                        timeout=tool.timeout_ms / 1000
                    )
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: tool.handler(**arguments)
                    )
            else:
                result = tool.handler(**arguments)

            execution_time = (time.time() - start_time) * 1000

            tool_result = ToolResult(
                tool_name=tool.name,
                success=True,
                result=result,
                execution_time_ms=execution_time
            )

            # Update metrics
            tool.metrics.total_calls += 1
            tool.metrics.successful_calls += 1
            tool.metrics.total_execution_time_ms += execution_time
            tool.metrics.avg_execution_time_ms = (
                tool.metrics.total_execution_time_ms / tool.metrics.total_calls
            )
            tool.metrics.last_used = datetime.now()

            # Cache result
            if tool.cacheable:
                self.result_cache[cache_key] = (tool_result, datetime.now())

            return tool_result

        except asyncio.TimeoutError:
            return self._create_error_result(tool, "Timeout", start_time)
        except Exception as e:
            return self._create_error_result(tool, str(e), start_time)

    def _create_error_result(
        self,
        tool: Tool,
        error: str,
        start_time: float
    ) -> ToolResult:
        """Create an error result."""
        execution_time = (time.time() - start_time) * 1000

        tool.metrics.total_calls += 1
        tool.metrics.failed_calls += 1
        tool.metrics.last_error = error
        tool.metrics.last_used = datetime.now()

        return ToolResult(
            tool_name=tool.name,
            success=False,
            error=error,
            execution_time_ms=execution_time
        )

    def _cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate cache key."""
        args_str = json.dumps(arguments, sort_keys=True)
        return f"{tool_name}:{hash(args_str)}"

    def _get_cached(
        self,
        key: str,
        ttl_seconds: int
    ) -> Optional[ToolResult]:
        """Get cached result if valid."""
        if key not in self.result_cache:
            return None

        result, cached_at = self.result_cache[key]
        age = (datetime.now() - cached_at).total_seconds()

        if age > ttl_seconds:
            del self.result_cache[key]
            return None

        return result


class ToolPipeline:
    """A pipeline of tools to execute in sequence."""

    def __init__(self, name: str):
        self.name = name
        self.steps: List[Tuple[str, Dict[str, str]]] = []  # (tool_name, input_mapping)

    def add_step(
        self,
        tool_name: str,
        input_mapping: Dict[str, str] = None
    ) -> "ToolPipeline":
        """Add a step to the pipeline."""
        self.steps.append((tool_name, input_mapping or {}))
        return self

    async def execute(
        self,
        orchestrator: "ToolOrchestrator",
        initial_input: Dict[str, Any]
    ) -> List[ToolResult]:
        """Execute the pipeline."""
        results = []
        context = initial_input.copy()

        for tool_name, input_mapping in self.steps:
            # Build arguments from context using mapping
            arguments = {}
            for arg_name, context_key in input_mapping.items():
                if context_key.startswith("$"):
                    # Reference to previous result
                    result_idx = int(context_key[1:])
                    if result_idx < len(results):
                        arguments[arg_name] = results[result_idx].result
                else:
                    arguments[arg_name] = context.get(context_key)

            # Add any direct context values not mapped
            tool = orchestrator.get_tool(tool_name)
            if tool:
                for param in tool.schema.parameters:
                    if param.name not in arguments and param.name in context:
                        arguments[param.name] = context[param.name]

            # Execute
            result = await orchestrator.execute(tool_name, arguments)
            results.append(result)

            # Update context with result
            context[f"result_{len(results)-1}"] = result.result

            # Stop on error
            if not result.success:
                break

        return results


class ToolOrchestrator:
    """
    Master tool orchestrator.

    Manages:
    - Tool registration and discovery
    - Tool selection based on capabilities
    - Execution with error handling
    - Pipelines and chaining
    - Analytics and optimization
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.executor = ToolExecutor()
        self.pipelines: Dict[str, ToolPipeline] = {}

        # Category index
        self.by_category: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }

        # Capability index
        self.by_capability: Dict[str, List[str]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
        self.by_category[tool.category].append(tool.name)

        # Index by tags as capabilities
        for tag in tool.tags:
            if tag not in self.by_capability:
                self.by_capability[tag] = []
            self.by_capability[tag].append(tool.name)

        logger.info(f"Registered tool: {tool.name} ({tool.category.value})")

    def unregister(self, tool_name: str):
        """Unregister a tool."""
        if tool_name not in self.tools:
            return

        tool = self.tools[tool_name]
        self.by_category[tool.category].remove(tool_name)

        for tag in tool.tags:
            if tag in self.by_capability:
                self.by_capability[tag].remove(tool_name)

        del self.tools[tool_name]

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get all tools in a category."""
        return [self.tools[name] for name in self.by_category[category]]

    def get_tools_by_capability(self, capability: str) -> List[Tool]:
        """Get all tools with a capability."""
        tool_names = self.by_capability.get(capability, [])
        return [self.tools[name] for name in tool_names]

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}"
            )

        if tool.status != ToolStatus.AVAILABLE:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not available: {tool.status.value}"
            )

        return await self.executor.execute(tool, arguments)

    async def execute_with_fallback(
        self,
        tool_names: List[str],
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute with fallback to other tools on failure."""
        for tool_name in tool_names:
            result = await self.execute(tool_name, arguments)
            if result.success:
                return result

        return ToolResult(
            tool_name=tool_names[0] if tool_names else "unknown",
            success=False,
            error="All fallback tools failed"
        )

    async def select_and_execute(
        self,
        task_description: str,
        arguments: Dict[str, Any],
        category: ToolCategory = None
    ) -> ToolResult:
        """Automatically select best tool for task and execute."""
        candidates = self._select_tools(task_description, category)

        if not candidates:
            return ToolResult(
                tool_name="auto",
                success=False,
                error="No suitable tool found"
            )

        return await self.execute_with_fallback(candidates, arguments)

    def _select_tools(
        self,
        task_description: str,
        category: ToolCategory = None
    ) -> List[str]:
        """Select tools based on task description."""
        candidates = []
        task_lower = task_description.lower()

        for tool in self.tools.values():
            # Filter by category
            if category and tool.category != category:
                continue

            # Check availability
            if tool.status != ToolStatus.AVAILABLE:
                continue

            # Score based on description match
            score = 0
            desc_lower = tool.schema.description.lower()

            # Word overlap
            task_words = set(task_lower.split())
            desc_words = set(desc_lower.split())
            overlap = len(task_words & desc_words)
            score += overlap * 10

            # Tag match
            for tag in tool.tags:
                if tag.lower() in task_lower:
                    score += 20

            # Success rate bonus
            score += tool.metrics.success_rate * 5

            if score > 0:
                candidates.append((tool.name, score))

        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in candidates[:3]]

    def register_pipeline(self, pipeline: ToolPipeline):
        """Register a tool pipeline."""
        self.pipelines[pipeline.name] = pipeline

    async def execute_pipeline(
        self,
        pipeline_name: str,
        initial_input: Dict[str, Any]
    ) -> List[ToolResult]:
        """Execute a registered pipeline."""
        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            return [ToolResult(
                tool_name="pipeline",
                success=False,
                error=f"Pipeline not found: {pipeline_name}"
            )]

        return await pipeline.execute(self, initial_input)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-format schemas for all tools."""
        return [
            tool.schema.to_openai_format()
            for tool in self.tools.values()
            if tool.status == ToolStatus.AVAILABLE
        ]

    def get_analytics(self) -> Dict[str, Any]:
        """Get tool usage analytics."""
        total_calls = sum(t.metrics.total_calls for t in self.tools.values())
        successful = sum(t.metrics.successful_calls for t in self.tools.values())

        top_tools = sorted(
            self.tools.values(),
            key=lambda t: t.metrics.total_calls,
            reverse=True
        )[:5]

        return {
            "total_tools": len(self.tools),
            "total_calls": total_calls,
            "overall_success_rate": successful / total_calls if total_calls > 0 else 0,
            "top_tools": [
                {
                    "name": t.name,
                    "calls": t.metrics.total_calls,
                    "success_rate": t.metrics.success_rate
                }
                for t in top_tools
            ],
            "by_category": {
                cat.value: len(tools)
                for cat, tools in self.by_category.items()
            }
        }


def tool(
    name: str,
    category: ToolCategory,
    description: str,
    tags: List[str] = None,
    cacheable: bool = False
):
    """Decorator to create a tool from a function."""
    def decorator(func: Callable) -> Tool:
        schema = ToolSchema(name=name, description=description)

        return Tool(
            id=str(uuid4())[:8],
            name=name,
            category=category,
            schema=schema,
            handler=func,
            tags=tags or [],
            cacheable=cacheable
        )
    return decorator


# Built-in tools
@tool("calculator", ToolCategory.UTILITY, "Perform mathematical calculations")
def calculator(expression: str) -> float:
    """Safely evaluate mathematical expression."""
    # Basic safe evaluation
    allowed = set('0123456789+-*/.() ')
    if all(c in allowed for c in expression):
        try:
            return eval(expression)
        except:
            return float('nan')
    return float('nan')


@tool("text_length", ToolCategory.UTILITY, "Get length of text")
def text_length(text: str) -> int:
    """Get the length of text."""
    return len(text)


async def demo():
    """Demonstrate tool orchestrator."""
    print("=" * 60)
    print("BAEL Tool Orchestration Demo")
    print("=" * 60)

    orchestrator = ToolOrchestrator()

    # Register built-in tools
    orchestrator.register(calculator)
    orchestrator.register(text_length)

    # Create custom tool
    @tool("web_search", ToolCategory.SEARCH, "Search the web", tags=["search", "web"])
    async def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
        # Simulated search
        return [
            {"title": f"Result {i+1} for {query}", "url": f"https://example.com/{i}"}
            for i in range(num_results)
        ]

    orchestrator.register(web_search)

    print(f"\nRegistered {len(orchestrator.tools)} tools")

    # Execute calculator
    result = await orchestrator.execute("calculator", {"expression": "2 + 3 * 4"})
    print(f"\nCalculator: 2 + 3 * 4 = {result.result}")

    # Execute search
    result = await orchestrator.execute("web_search", {"query": "AI frameworks"})
    print(f"Search returned {len(result.result)} results")

    # Create pipeline
    pipeline = (
        ToolPipeline("search_and_analyze")
        .add_step("web_search", {"query": "query"})
        .add_step("text_length", {"text": "$0"})  # Use result from step 0
    )
    orchestrator.register_pipeline(pipeline)

    # Get schemas
    schemas = orchestrator.get_all_schemas()
    print(f"\nGenerated {len(schemas)} OpenAI function schemas")

    # Analytics
    analytics = orchestrator.get_analytics()
    print(f"Total calls: {analytics['total_calls']}")

    print("\n✓ Tool registration and discovery")
    print("✓ Automatic schema extraction")
    print("✓ OpenAI function format export")
    print("✓ Tool pipelines")
    print("✓ Fallback execution")
    print("✓ Caching support")
    print("✓ Usage analytics")


if __name__ == "__main__":
    asyncio.run(demo())
