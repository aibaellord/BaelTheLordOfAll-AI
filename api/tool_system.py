"""
Standardized tool interface and plugin system.
Enables easy tool creation, registration, and extensibility.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.ToolSystem")


class ToolStatus(str, Enum):
    """Tool status enumeration."""
    AVAILABLE = "available"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


class ToolCategory(str, Enum):
    """Tool category enumeration."""
    EXECUTION = "execution"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"
    UTILITY = "utility"
    RESEARCH = "research"
    DEVELOPMENT = "development"


@dataclass
class ToolParameter:
    """Tool parameter schema."""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None


@dataclass
class ToolResponse:
    """Standard tool response."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, tool_id: str, name: str, description: str,
                 category: ToolCategory, parameters: Optional[List[ToolParameter]] = None):
        self.id = tool_id
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters or []
        self.status = ToolStatus.AVAILABLE
        self.enabled = True
        self.usage_count = 0
        self.success_count = 0
        self.error_count = 0

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResponse:
        """Execute the tool with given parameters."""
        pass

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input parameters against schema."""
        # Check required parameters
        required_params = {p.name for p in self.parameters if p.required}
        provided_params = set(kwargs.keys())

        missing = required_params - provided_params
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"

        # Validate each parameter
        for param in self.parameters:
            if param.name not in kwargs:
                continue

            value = kwargs[param.name]

            # Type checking
            if param.type == "string" and not isinstance(value, str):
                return False, f"Parameter {param.name} must be a string"
            elif param.type == "number" and not isinstance(value, (int, float)):
                return False, f"Parameter {param.name} must be a number"
            elif param.type == "boolean" and not isinstance(value, bool):
                return False, f"Parameter {param.name} must be a boolean"

            # Value range checking
            if param.min_value is not None and value < param.min_value:
                return False, f"Parameter {param.name} must be >= {param.min_value}"
            if param.max_value is not None and value > param.max_value:
                return False, f"Parameter {param.name} must be <= {param.max_value}"

            # Enum checking
            if param.enum and value not in param.enum:
                return False, f"Parameter {param.name} must be one of {param.enum}"

        return True, None

    def record_execution(self, success: bool = True):
        """Record tool execution."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        logger.debug(f"Tool {self.name} executed: {self.usage_count} total, {self.success_count} successful")

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for API documentation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "enabled": self.enabled,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                    "min_value": p.min_value,
                    "max_value": p.max_value
                }
                for p in self.parameters
            ],
            "usage_stats": {
                "total_executions": self.usage_count,
                "successful": self.success_count,
                "failed": self.error_count,
                "success_rate": self.success_count / self.usage_count if self.usage_count > 0 else 0
            }
        }


class ToolRegistry:
    """Registry for managing tools and plugins."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.plugin_loaders: List[Callable] = []

    def register_tool(self, tool: BaseTool) -> bool:
        """Register a tool."""
        if tool.id in self.tools:
            logger.warning(f"Tool {tool.id} already registered, skipping")
            return False

        self.tools[tool.id] = tool
        logger.info(f"Registered tool: {tool.name} (ID: {tool.id})")
        return True

    def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool."""
        if tool_id not in self.tools:
            logger.warning(f"Tool {tool_id} not found")
            return False

        del self.tools[tool_id]
        logger.info(f"Unregistered tool: {tool_id}")
        return True

    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)

    def list_tools(self, category: Optional[ToolCategory] = None,
                   enabled_only: bool = True) -> List[Dict[str, Any]]:
        """List all tools or filter by category."""
        tools = self.tools.values()

        if category:
            tools = [t for t in tools if t.category == category]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return [t.get_schema() for t in tools]

    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self.tools)

    async def execute_tool(self, tool_id: str, **kwargs) -> ToolResponse:
        """Execute a tool safely."""
        tool = self.get_tool(tool_id)
        if not tool:
            return ToolResponse(
                success=False,
                error=f"Tool {tool_id} not found"
            )

        if not tool.enabled:
            return ToolResponse(
                success=False,
                error=f"Tool {tool.name} is disabled"
            )

        # Validate parameters
        valid, error_msg = tool.validate_parameters(**kwargs)
        if not valid:
            return ToolResponse(
                success=False,
                error=error_msg
            )

        # Execute tool
        try:
            result = await tool.execute(**kwargs)
            tool.record_execution(result.success)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_id}: {str(e)}")
            tool.record_execution(False)
            return ToolResponse(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    def register_plugin_loader(self, loader: Callable):
        """Register a plugin loader function."""
        self.plugin_loaders.append(loader)
        logger.info(f"Registered plugin loader: {loader.__name__}")

    async def load_plugins(self):
        """Load all registered plugins."""
        for loader in self.plugin_loaders:
            try:
                await loader(self)
                logger.info(f"Loaded plugin from {loader.__name__}")
            except Exception as e:
                logger.error(f"Error loading plugin {loader.__name__}: {str(e)}")

    def export_tools(self) -> str:
        """Export all tools as JSON."""
        tools_data = [tool.get_schema() for tool in self.tools.values()]
        return json.dumps(tools_data, indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        """Get tool registry statistics."""
        total_usage = sum(t.usage_count for t in self.tools.values())
        total_success = sum(t.success_count for t in self.tools.values())
        total_errors = sum(t.error_count for t in self.tools.values())

        return {
            "total_tools": len(self.tools),
            "enabled_tools": sum(1 for t in self.tools.values() if t.enabled),
            "total_executions": total_usage,
            "total_successful": total_success,
            "total_errors": total_errors,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0
        }


# Global tool registry instance
tool_registry = ToolRegistry()
