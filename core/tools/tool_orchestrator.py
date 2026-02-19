"""
🔧 BAEL TOOL ORCHESTRATION ENGINE
==================================
Advanced tool discovery, orchestration, and chaining system.

Features:
- Dynamic tool discovery (MCP, local, remote)
- Intelligent tool selection
- Tool chaining and pipelines
- Parallel tool execution
- Result aggregation
- Tool learning and optimization
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

logger = logging.getLogger("BAEL.ToolOrchestration")


class ToolCategory(Enum):
    """Categories of tools"""
    WEB = "web"               # Web scraping, search, fetch
    CODE = "code"             # Code execution, analysis
    FILE = "file"             # File operations
    DATABASE = "database"     # Database operations
    AI = "ai"                 # AI/LLM operations
    API = "api"               # External API calls
    SYSTEM = "system"         # System operations
    COMMUNICATION = "communication"  # Email, messaging
    PERCEPTION = "perception" # Vision, audio
    ACTION = "action"         # Mouse, keyboard
    CUSTOM = "custom"         # User-defined


class ToolStatus(Enum):
    """Tool status"""
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"
    RATE_LIMITED = "rate_limited"


class ChainType(Enum):
    """Types of tool chains"""
    SEQUENTIAL = "sequential"   # A → B → C
    PARALLEL = "parallel"       # A + B + C
    CONDITIONAL = "conditional" # A → (B or C) based on condition
    PIPELINE = "pipeline"       # A → B → C with data flow
    FALLBACK = "fallback"       # A, if fail B, if fail C


@dataclass
class ToolParameter:
    """A tool parameter"""
    name: str
    param_type: str  # "string", "number", "boolean", "object", "array"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: List[Any] = field(default_factory=list)


@dataclass
class ToolSchema:
    """Schema for a tool"""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "any"
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.param_type,
                        "description": p.description,
                        **({"enum": p.enum} if p.enum else {}),
                        **({"default": p.default} if p.default is not None else {})
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    output: Any = None
    error: Optional[str] = None

    # Performance
    execution_time_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0

    # Metadata
    tool_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name
        }


class Tool(ABC):
    """Base class for all tools"""

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.CUSTOM
    ):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.category = category
        self.status = ToolStatus.AVAILABLE

        # Performance tracking
        self.usage_count = 0
        self.success_count = 0
        self.total_execution_time = 0.0
        self.last_used: Optional[datetime] = None

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get tool schema"""
        pass

    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """Execute the tool"""
        pass

    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.usage_count == 0:
            return 1.0
        return self.success_count / self.usage_count

    def get_avg_execution_time(self) -> float:
        """Get average execution time"""
        if self.usage_count == 0:
            return 0.0
        return self.total_execution_time / self.usage_count


class MCPTool(Tool):
    """Tool from MCP server"""

    def __init__(
        self,
        name: str,
        description: str,
        server_name: str,
        schema: Dict[str, Any]
    ):
        super().__init__(name, description, ToolCategory.CUSTOM)
        self.server_name = server_name
        self._schema = schema
        self._mcp_client = None

    def get_schema(self) -> ToolSchema:
        params = []
        props = self._schema.get("inputSchema", {}).get("properties", {})
        required = self._schema.get("inputSchema", {}).get("required", [])

        for name, prop in props.items():
            params.append(ToolParameter(
                name=name,
                param_type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required
            ))

        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=params
        )

    async def execute(self, **params) -> ToolResult:
        """Execute MCP tool"""
        start = datetime.now()

        try:
            # In real impl, call MCP client
            result = {"status": "mcp_call_simulated", "params": params}

            execution_time = (datetime.now() - start).total_seconds() * 1000

            self.usage_count += 1
            self.success_count += 1
            self.total_execution_time += execution_time
            self.last_used = datetime.now()

            return ToolResult(
                success=True,
                output=result,
                execution_time_ms=execution_time,
                tool_name=self.name
            )

        except Exception as e:
            self.usage_count += 1
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


class FunctionTool(Tool):
    """Tool wrapping a Python function"""

    def __init__(
        self,
        func: Callable,
        name: str = None,
        description: str = None,
        category: ToolCategory = ToolCategory.CUSTOM
    ):
        name = name or func.__name__
        description = description or func.__doc__ or ""
        super().__init__(name, description, category)
        self.func = func
        self._params = self._extract_params()

    def _extract_params(self) -> List[ToolParameter]:
        """Extract parameters from function"""
        import inspect
        sig = inspect.signature(self.func)
        params = []

        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "number",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")

            params.append(ToolParameter(
                name=name,
                param_type=param_type,
                required=param.default == inspect.Parameter.empty,
                default=None if param.default == inspect.Parameter.empty else param.default
            ))

        return params

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self._params
        )

    async def execute(self, **params) -> ToolResult:
        """Execute function"""
        start = datetime.now()

        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(**params)
            else:
                result = self.func(**params)

            execution_time = (datetime.now() - start).total_seconds() * 1000

            self.usage_count += 1
            self.success_count += 1
            self.total_execution_time += execution_time
            self.last_used = datetime.now()

            return ToolResult(
                success=True,
                output=result,
                execution_time_ms=execution_time,
                tool_name=self.name
            )

        except Exception as e:
            self.usage_count += 1
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


@dataclass
class ChainStep:
    """A step in a tool chain"""
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)

    # Data flow
    input_mapping: Dict[str, str] = field(default_factory=dict)  # param -> previous_output_key
    output_key: str = "result"

    # Control
    condition: Optional[str] = None  # Expression to evaluate
    on_error: str = "stop"  # "stop", "skip", "fallback"
    fallback_tool: Optional[str] = None

    # Timeout
    timeout_seconds: int = 60


@dataclass
class ToolChain:
    """A chain of tools"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    chain_type: ChainType = ChainType.SEQUENTIAL

    # Steps
    steps: List[ChainStep] = field(default_factory=list)

    # Execution
    timeout_seconds: int = 300
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "chain_type": self.chain_type.value,
            "steps": len(self.steps)
        }


@dataclass
class ChainResult:
    """Result from chain execution"""
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    step_results: List[ToolResult] = field(default_factory=list)
    total_time_ms: float = 0.0


class ToolDiscovery:
    """Discover available tools"""

    def __init__(self):
        self.discovered_tools: Dict[str, Tool] = {}
        self.mcp_servers: List[str] = []

    async def discover_mcp_tools(self, server_uri: str) -> List[Tool]:
        """Discover tools from MCP server"""
        tools = []

        try:
            # In real impl, connect to MCP server and list tools
            # For now, simulate
            logger.info(f"Discovering tools from MCP server: {server_uri}")

            # Example discovered tools
            mcp_tools = [
                {"name": "search", "description": "Web search", "server": server_uri},
                {"name": "fetch", "description": "Fetch URL", "server": server_uri}
            ]

            for tool_data in mcp_tools:
                tool = MCPTool(
                    name=f"{server_uri}_{tool_data['name']}",
                    description=tool_data["description"],
                    server_name=server_uri,
                    schema={}
                )
                tools.append(tool)
                self.discovered_tools[tool.name] = tool

        except Exception as e:
            logger.error(f"MCP discovery failed: {e}")

        return tools

    def discover_local_tools(self, module_path: str) -> List[Tool]:
        """Discover tools from local module"""
        tools = []

        try:
            # Would dynamically import and discover tools
            logger.info(f"Discovering tools from: {module_path}")

        except Exception as e:
            logger.error(f"Local discovery failed: {e}")

        return tools

    def register_function(
        self,
        func: Callable,
        name: str = None,
        category: ToolCategory = ToolCategory.CUSTOM
    ) -> Tool:
        """Register a function as a tool"""
        tool = FunctionTool(func, name, category=category)
        self.discovered_tools[tool.name] = tool
        return tool


class ToolSelector:
    """Intelligently select tools for tasks"""

    def __init__(self, tools: Dict[str, Tool] = None):
        self.tools = tools or {}

        # Learning
        self.tool_scores: Dict[str, Dict[str, float]] = {}  # task_type -> tool -> score

    def select_tool(
        self,
        task_description: str,
        required_capabilities: List[str] = None,
        preferred_categories: List[ToolCategory] = None
    ) -> Optional[Tool]:
        """Select best tool for task"""
        candidates = list(self.tools.values())

        # Filter by status
        candidates = [t for t in candidates if t.status == ToolStatus.AVAILABLE]

        # Filter by category
        if preferred_categories:
            candidates = [t for t in candidates if t.category in preferred_categories]

        if not candidates:
            return None

        # Score candidates
        scored = []
        for tool in candidates:
            score = self._score_tool(tool, task_description)
            scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def _score_tool(self, tool: Tool, task: str) -> float:
        """Score tool for task"""
        score = 0.0

        # Description match
        task_words = set(task.lower().split())
        desc_words = set(tool.description.lower().split())
        overlap = len(task_words & desc_words)
        score += overlap * 0.2

        # Success rate
        score += tool.get_success_rate() * 0.3

        # Speed (inverse of avg time, normalized)
        avg_time = tool.get_avg_execution_time()
        if avg_time > 0:
            speed_score = min(1.0, 1000 / avg_time)
            score += speed_score * 0.2
        else:
            score += 0.5 * 0.2  # Neutral if no data

        # Recency (prefer recently used tools that worked)
        if tool.last_used and tool.get_success_rate() > 0.5:
            hours_since = (datetime.now() - tool.last_used).total_seconds() / 3600
            recency_score = max(0, 1 - hours_since / 168)  # Decay over a week
            score += recency_score * 0.3

        return score

    def select_tools_for_chain(
        self,
        task_steps: List[str]
    ) -> List[Tuple[str, Tool]]:
        """Select tools for each step in a task"""
        selections = []

        for step in task_steps:
            tool = self.select_tool(step)
            if tool:
                selections.append((step, tool))
            else:
                selections.append((step, None))

        return selections

    def update_score(
        self,
        tool_name: str,
        task_type: str,
        success: bool
    ) -> None:
        """Update tool score based on outcome"""
        if task_type not in self.tool_scores:
            self.tool_scores[task_type] = {}

        current = self.tool_scores[task_type].get(tool_name, 0.5)
        # Exponential moving average
        new_score = 0.8 * current + 0.2 * (1.0 if success else 0.0)
        self.tool_scores[task_type][tool_name] = new_score


class ChainExecutor:
    """Execute tool chains"""

    def __init__(self, tools: Dict[str, Tool] = None):
        self.tools = tools or {}

    async def execute_chain(
        self,
        chain: ToolChain,
        initial_input: Dict[str, Any] = None
    ) -> ChainResult:
        """Execute a tool chain"""
        start = datetime.now()

        if chain.chain_type == ChainType.SEQUENTIAL:
            return await self._execute_sequential(chain, initial_input)
        elif chain.chain_type == ChainType.PARALLEL:
            return await self._execute_parallel(chain, initial_input)
        elif chain.chain_type == ChainType.PIPELINE:
            return await self._execute_pipeline(chain, initial_input)
        elif chain.chain_type == ChainType.FALLBACK:
            return await self._execute_fallback(chain, initial_input)
        else:
            return ChainResult(success=False, errors=["Unknown chain type"])

    async def _execute_sequential(
        self,
        chain: ToolChain,
        initial_input: Dict[str, Any]
    ) -> ChainResult:
        """Execute steps sequentially"""
        outputs = dict(initial_input or {})
        step_results = []
        errors = []

        for step in chain.steps:
            tool = self.tools.get(step.tool_name)
            if not tool:
                errors.append(f"Tool not found: {step.tool_name}")
                continue

            # Map inputs
            params = dict(step.params)
            for param, output_key in step.input_mapping.items():
                if output_key in outputs:
                    params[param] = outputs[output_key]

            # Execute
            try:
                result = await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=step.timeout_seconds
                )
                step_results.append(result)

                if result.success:
                    outputs[step.output_key] = result.output
                else:
                    errors.append(f"{step.tool_name}: {result.error}")
                    if step.on_error == "stop":
                        break

            except asyncio.TimeoutError:
                errors.append(f"{step.tool_name}: timeout")
                if step.on_error == "stop":
                    break

        total_time = sum(r.execution_time_ms for r in step_results)

        return ChainResult(
            success=len(errors) == 0,
            outputs=outputs,
            errors=errors,
            step_results=step_results,
            total_time_ms=total_time
        )

    async def _execute_parallel(
        self,
        chain: ToolChain,
        initial_input: Dict[str, Any]
    ) -> ChainResult:
        """Execute steps in parallel"""
        outputs = dict(initial_input or {})
        step_results = []
        errors = []

        async def execute_step(step: ChainStep) -> Tuple[str, ToolResult]:
            tool = self.tools.get(step.tool_name)
            if not tool:
                return step.output_key, ToolResult(success=False, error="Tool not found")

            params = dict(step.params)
            for param, output_key in step.input_mapping.items():
                if output_key in outputs:
                    params[param] = outputs[output_key]

            try:
                result = await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=step.timeout_seconds
                )
                return step.output_key, result
            except asyncio.TimeoutError:
                return step.output_key, ToolResult(success=False, error="timeout")

        # Execute all in parallel
        tasks = [execute_step(step) for step in chain.steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for output_key, result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif isinstance(result, ToolResult):
                step_results.append(result)
                if result.success:
                    outputs[output_key] = result.output
                else:
                    errors.append(f"{result.tool_name}: {result.error}")

        total_time = max((r.execution_time_ms for r in step_results), default=0)

        return ChainResult(
            success=len(errors) == 0,
            outputs=outputs,
            errors=errors,
            step_results=step_results,
            total_time_ms=total_time
        )

    async def _execute_pipeline(
        self,
        chain: ToolChain,
        initial_input: Dict[str, Any]
    ) -> ChainResult:
        """Execute as pipeline (output of A is input of B)"""
        data = initial_input or {}
        step_results = []
        errors = []

        for step in chain.steps:
            tool = self.tools.get(step.tool_name)
            if not tool:
                errors.append(f"Tool not found: {step.tool_name}")
                break

            # Previous output becomes input
            params = dict(step.params)
            params.update(data)

            try:
                result = await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=step.timeout_seconds
                )
                step_results.append(result)

                if result.success:
                    if isinstance(result.output, dict):
                        data = result.output
                    else:
                        data = {"result": result.output}
                else:
                    errors.append(f"{step.tool_name}: {result.error}")
                    break

            except asyncio.TimeoutError:
                errors.append(f"{step.tool_name}: timeout")
                break

        return ChainResult(
            success=len(errors) == 0,
            outputs=data,
            errors=errors,
            step_results=step_results,
            total_time_ms=sum(r.execution_time_ms for r in step_results)
        )

    async def _execute_fallback(
        self,
        chain: ToolChain,
        initial_input: Dict[str, Any]
    ) -> ChainResult:
        """Execute with fallback (try A, if fail try B, etc.)"""
        outputs = dict(initial_input or {})
        step_results = []
        errors = []

        for step in chain.steps:
            tool = self.tools.get(step.tool_name)
            if not tool:
                errors.append(f"Tool not found: {step.tool_name}")
                continue

            params = dict(step.params)
            for param, output_key in step.input_mapping.items():
                if output_key in outputs:
                    params[param] = outputs[output_key]

            try:
                result = await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=step.timeout_seconds
                )
                step_results.append(result)

                if result.success:
                    outputs[step.output_key] = result.output
                    # Success - stop trying fallbacks
                    return ChainResult(
                        success=True,
                        outputs=outputs,
                        step_results=step_results,
                        total_time_ms=sum(r.execution_time_ms for r in step_results)
                    )
                else:
                    errors.append(f"{step.tool_name}: {result.error}")
                    # Continue to next fallback

            except asyncio.TimeoutError:
                errors.append(f"{step.tool_name}: timeout")
                # Continue to next fallback

        # All failed
        return ChainResult(
            success=False,
            outputs=outputs,
            errors=errors,
            step_results=step_results,
            total_time_ms=sum(r.execution_time_ms for r in step_results)
        )


class ToolOrchestrator:
    """
    The COMPLETE Tool Orchestration Engine.

    Provides:
    - Dynamic tool discovery (MCP, local, remote)
    - Intelligent tool selection
    - Tool chaining and pipelines
    - Parallel execution
    - Learning from outcomes
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}

        # Components
        self.discovery = ToolDiscovery()
        self.selector = ToolSelector()
        self.chain_executor = ChainExecutor()

        # State
        self.tools: Dict[str, Tool] = {}
        self.chains: Dict[str, ToolChain] = {}

        # Statistics
        self.execution_count = 0
        self.total_execution_time = 0.0

    async def initialize(self) -> None:
        """Initialize orchestrator"""
        logger.info("Initializing Tool Orchestrator")

        # Discover MCP tools
        mcp_servers = [
            "filesystem", "brave-search", "github", "sqlite", "memory"
        ]

        for server in mcp_servers:
            await self.discovery.discover_mcp_tools(server)

        # Update tool references
        self.tools = self.discovery.discovered_tools
        self.selector.tools = self.tools
        self.chain_executor.tools = self.tools

        logger.info(f"Discovered {len(self.tools)} tools")

    def register_tool(self, tool: Tool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool
        self.selector.tools = self.tools
        self.chain_executor.tools = self.tools
        logger.info(f"Registered tool: {tool.name}")

    def register_function(
        self,
        func: Callable,
        name: str = None,
        category: ToolCategory = ToolCategory.CUSTOM
    ) -> Tool:
        """Register a function as a tool"""
        tool = self.discovery.register_function(func, name, category)
        self.tools[tool.name] = tool
        self.selector.tools = self.tools
        self.chain_executor.tools = self.tools
        return tool

    async def execute_tool(
        self,
        tool_name: str,
        **params
    ) -> ToolResult:
        """Execute a single tool"""
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        tool = self.tools[tool_name]
        result = await tool.execute(**params)

        self.execution_count += 1
        self.total_execution_time += result.execution_time_ms

        return result

    async def execute_for_task(
        self,
        task_description: str,
        **params
    ) -> ToolResult:
        """Select and execute best tool for task"""
        tool = self.selector.select_tool(task_description)

        if not tool:
            return ToolResult(
                success=False,
                error="No suitable tool found for task"
            )

        result = await tool.execute(**params)

        # Update selector learning
        self.selector.update_score(
            tool.name,
            task_description.split()[0],  # First word as task type
            result.success
        )

        return result

    def create_chain(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        chain_type: ChainType = ChainType.SEQUENTIAL
    ) -> ToolChain:
        """Create a tool chain"""
        chain_steps = []

        for step_data in steps:
            step = ChainStep(
                tool_name=step_data["tool"],
                params=step_data.get("params", {}),
                input_mapping=step_data.get("input_mapping", {}),
                output_key=step_data.get("output_key", "result")
            )
            chain_steps.append(step)

        chain = ToolChain(
            name=name,
            chain_type=chain_type,
            steps=chain_steps
        )

        self.chains[chain.id] = chain
        return chain

    async def execute_chain(
        self,
        chain_id: str,
        initial_input: Dict[str, Any] = None
    ) -> ChainResult:
        """Execute a tool chain"""
        if chain_id not in self.chains:
            return ChainResult(success=False, errors=["Chain not found"])

        chain = self.chains[chain_id]
        result = await self.chain_executor.execute_chain(chain, initial_input)

        self.execution_count += len(result.step_results)
        self.total_execution_time += result.total_time_ms

        return result

    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Get list of all tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "status": tool.status.value,
                "usage_count": tool.usage_count,
                "success_rate": tool.get_success_rate(),
                "avg_time_ms": tool.get_avg_execution_time()
            }
            for tool in self.tools.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "total_tools": len(self.tools),
            "available_tools": sum(1 for t in self.tools.values() if t.status == ToolStatus.AVAILABLE),
            "chains": len(self.chains),
            "total_executions": self.execution_count,
            "avg_execution_time_ms": self.total_execution_time / max(1, self.execution_count),
            "categories": {
                cat.value: sum(1 for t in self.tools.values() if t.category == cat)
                for cat in ToolCategory
            }
        }


# Factory function
async def create_tool_orchestrator(**config) -> ToolOrchestrator:
    """Create and initialize tool orchestrator"""
    orchestrator = ToolOrchestrator(config)
    await orchestrator.initialize()
    return orchestrator


__all__ = [
    'ToolOrchestrator',
    'Tool',
    'MCPTool',
    'FunctionTool',
    'ToolSchema',
    'ToolParameter',
    'ToolResult',
    'ToolChain',
    'ChainStep',
    'ChainResult',
    'ToolCategory',
    'ToolStatus',
    'ChainType',
    'ToolDiscovery',
    'ToolSelector',
    'ChainExecutor',
    'create_tool_orchestrator'
]
