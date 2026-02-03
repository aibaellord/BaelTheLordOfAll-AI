"""
BAEL - Unified Tools System
Comprehensive toolkit for all agent operations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("BAEL.Tools")


class ToolCategory(Enum):
    """Categories of tools."""
    WEB = "web"
    CODE = "code"
    FILE = "file"
    DATABASE = "database"
    AI = "ai"
    API = "api"
    SYSTEM = "system"
    RESEARCH = "research"
    COMMUNICATION = "communication"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDefinition:
    """Definition of a tool."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    timeout_seconds: int = 30


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str, category: ToolCategory):
        self.name = name
        self.description = description
        self.category = category
        self._enabled = True

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        pass

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Get tool definition."""
        pass

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._by_category: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        self._by_category[tool.category].append(tool.name)
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def list_by_category(self, category: ToolCategory) -> List[str]:
        """List tools by category."""
        return self._by_category.get(category, [])

    def get_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions."""
        return [tool.get_definition() for tool in self._tools.values()]

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}"
            )

        if not tool.is_enabled:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool is disabled: {name}"
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool execution failed: {name} - {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class ToolLoader:
    """Loads and initializes tools."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._tool_classes: Dict[str, Type[BaseTool]] = {}

    def register_class(self, name: str, tool_class: Type[BaseTool]) -> None:
        """Register a tool class for lazy loading."""
        self._tool_classes[name] = tool_class

    def load_tool(self, name: str, **config) -> Optional[BaseTool]:
        """Load and instantiate a tool."""
        tool_class = self._tool_classes.get(name)
        if not tool_class:
            logger.warning(f"Tool class not found: {name}")
            return None

        try:
            tool = tool_class(**config)
            self.registry.register(tool)
            return tool
        except Exception as e:
            logger.error(f"Failed to load tool {name}: {e}")
            return None

    def load_all(self, config: Dict[str, Dict] = None) -> int:
        """Load all registered tool classes."""
        config = config or {}
        loaded = 0

        for name, tool_class in self._tool_classes.items():
            tool_config = config.get(name, {})
            if self.load_tool(name, **tool_config):
                loaded += 1

        return loaded


# Global registry
registry = ToolRegistry()
loader = ToolLoader(registry)


__all__ = [
    "ToolCategory",
    "ToolResult",
    "ToolDefinition",
    "BaseTool",
    "ToolRegistry",
    "ToolLoader",
    "registry",
    "loader"
]
