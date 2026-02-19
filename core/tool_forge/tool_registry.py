"""
BAEL Tool Registry
===================

Dynamic tool registration and discovery.
Central catalog for all available tools.

Features:
- Dynamic registration
- Category organization
- Version management
- Dependency tracking
- Tool discovery
"""

import asyncio
import hashlib
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool categories."""
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    TEXT_PROCESSING = "text_processing"
    MATH = "math"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    API = "api"
    DATABASE = "database"
    SYSTEM = "system"
    AI = "ai"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """Tool status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    author: str = "system"
    version: str = "1.0.0"

    # Documentation
    description: str = ""
    usage_examples: List[str] = field(default_factory=list)

    # Tags
    tags: List[str] = field(default_factory=list)

    # Performance
    avg_execution_time_ms: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RegisteredTool:
    """A registered tool in the system."""
    id: str
    name: str

    # Function
    function: Callable

    # Classification
    category: ToolCategory = ToolCategory.CUSTOM
    status: ToolStatus = ToolStatus.ACTIVE

    # Signature
    parameters: Dict[str, str] = field(default_factory=dict)
    return_type: str = "Any"
    is_async: bool = False

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Metadata
    metadata: ToolMetadata = field(default_factory=ToolMetadata)

    # Usage tracking
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0

    async def execute(self, *args, **kwargs) -> Any:
        """Execute the tool."""
        self.call_count += 1

        try:
            if self.is_async:
                result = await self.function(*args, **kwargs)
            else:
                result = self.function(*args, **kwargs)

            self.success_count += 1
            return result

        except Exception as e:
            self.error_count += 1
            raise


class ToolRegistry:
    """
    Tool registry for BAEL.

    Central catalog for dynamic tool management.
    """

    def __init__(self):
        # Registered tools
        self._tools: Dict[str, RegisteredTool] = {}

        # Index by category
        self._by_category: Dict[ToolCategory, Set[str]] = {
            cat: set() for cat in ToolCategory
        }

        # Index by tag
        self._by_tag: Dict[str, Set[str]] = {}

        # Aliases
        self._aliases: Dict[str, str] = {}

        # Stats
        self.stats = {
            "tools_registered": 0,
            "tools_deprecated": 0,
            "total_calls": 0,
        }

    def register(
        self,
        function: Callable,
        name: Optional[str] = None,
        category: ToolCategory = ToolCategory.CUSTOM,
        description: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
    ) -> RegisteredTool:
        """
        Register a tool.

        Args:
            function: Tool function
            name: Tool name (defaults to function name)
            category: Tool category
            description: Tool description
            tags: Tool tags
            version: Tool version
            dependencies: Required dependencies

        Returns:
            Registered tool
        """
        name = name or function.__name__

        tool_id = hashlib.md5(
            f"{name}:{version}".encode()
        ).hexdigest()[:12]

        # Extract signature
        sig = inspect.signature(function)
        parameters = {
            p.name: str(p.annotation) if p.annotation != inspect.Parameter.empty else "Any"
            for p in sig.parameters.values()
        }

        return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"

        # Check if async
        is_async = asyncio.iscoroutinefunction(function)

        # Create metadata
        metadata = ToolMetadata(
            version=version,
            description=description or function.__doc__ or "",
            tags=tags or [],
        )

        # Create tool
        tool = RegisteredTool(
            id=tool_id,
            name=name,
            function=function,
            category=category,
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            dependencies=dependencies or [],
            metadata=metadata,
        )

        # Register
        self._tools[tool_id] = tool
        self._by_category[category].add(tool_id)

        # Index by tags
        for tag in metadata.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(tool_id)

        self.stats["tools_registered"] += 1

        logger.info(f"Registered tool: {name} (id={tool_id})")

        return tool

    def register_alias(self, alias: str, tool_id: str) -> bool:
        """Register an alias for a tool."""
        if tool_id not in self._tools:
            return False

        self._aliases[alias] = tool_id
        return True

    def get(self, identifier: str) -> Optional[RegisteredTool]:
        """
        Get a tool by ID, name, or alias.

        Args:
            identifier: Tool ID, name, or alias

        Returns:
            Tool or None
        """
        # Direct ID lookup
        if identifier in self._tools:
            return self._tools[identifier]

        # Alias lookup
        if identifier in self._aliases:
            return self._tools.get(self._aliases[identifier])

        # Name search
        for tool in self._tools.values():
            if tool.name == identifier:
                return tool

        return None

    async def execute(
        self,
        identifier: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a tool by identifier.

        Args:
            identifier: Tool ID, name, or alias
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool result
        """
        tool = self.get(identifier)
        if not tool:
            raise ValueError(f"Unknown tool: {identifier}")

        if tool.status == ToolStatus.DISABLED:
            raise ValueError(f"Tool {tool.name} is disabled")

        self.stats["total_calls"] += 1

        return await tool.execute(*args, **kwargs)

    def deprecate(self, tool_id: str, replacement: Optional[str] = None) -> bool:
        """Deprecate a tool."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        tool.status = ToolStatus.DEPRECATED
        self.stats["tools_deprecated"] += 1

        if replacement:
            self._aliases[tool.name] = replacement

        logger.info(f"Deprecated tool: {tool.name}")

        return True

    def disable(self, tool_id: str) -> bool:
        """Disable a tool."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        tool.status = ToolStatus.DISABLED

        return True

    def search(
        self,
        query: str = "",
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ToolStatus] = None,
    ) -> List[RegisteredTool]:
        """
        Search for tools.

        Args:
            query: Search query
            category: Filter by category
            tags: Filter by tags
            status: Filter by status

        Returns:
            Matching tools
        """
        results = []

        for tool in self._tools.values():
            # Status filter
            if status and tool.status != status:
                continue

            # Category filter
            if category and tool.category != category:
                continue

            # Tag filter
            if tags:
                if not any(t in tool.metadata.tags for t in tags):
                    continue

            # Query match
            if query:
                query_lower = query.lower()
                if not any([
                    query_lower in tool.name.lower(),
                    query_lower in tool.metadata.description.lower(),
                    any(query_lower in t.lower() for t in tool.metadata.tags),
                ]):
                    continue

            results.append(tool)

        return results

    def by_category(
        self,
        category: ToolCategory,
    ) -> List[RegisteredTool]:
        """Get tools by category."""
        tool_ids = self._by_category.get(category, set())
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]

    def by_tag(self, tag: str) -> List[RegisteredTool]:
        """Get tools by tag."""
        tool_ids = self._by_tag.get(tag, set())
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]

    def list_all(self) -> List[RegisteredTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_categories(self) -> Dict[ToolCategory, int]:
        """List categories with tool counts."""
        return {
            cat: len(ids) for cat, ids in self._by_category.items()
        }

    def list_tags(self) -> Dict[str, int]:
        """List tags with tool counts."""
        return {
            tag: len(ids) for tag, ids in self._by_tag.items()
        }

    def unregister(self, tool_id: str) -> bool:
        """Unregister a tool."""
        tool = self._tools.get(tool_id)
        if not tool:
            return False

        # Remove from category index
        self._by_category[tool.category].discard(tool_id)

        # Remove from tag index
        for tag in tool.metadata.tags:
            if tag in self._by_tag:
                self._by_tag[tag].discard(tool_id)

        # Remove aliases
        for alias, tid in list(self._aliases.items()):
            if tid == tool_id:
                del self._aliases[alias]

        # Remove tool
        del self._tools[tool_id]

        logger.info(f"Unregistered tool: {tool.name}")

        return True

    def decorator(
        self,
        name: Optional[str] = None,
        category: ToolCategory = ToolCategory.CUSTOM,
        description: str = "",
        tags: Optional[List[str]] = None,
    ):
        """Decorator for registering tools."""
        def wrapper(func):
            self.register(
                func,
                name=name,
                category=category,
                description=description,
                tags=tags,
            )
            return func
        return wrapper

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        active = sum(1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE)

        return {
            **self.stats,
            "active_tools": active,
            "total_tools": len(self._tools),
            "categories_used": len([c for c, ids in self._by_category.items() if ids]),
            "tags_used": len(self._by_tag),
        }


# Global registry instance
_global_registry = None

def get_registry() -> ToolRegistry:
    """Get global registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def demo():
    """Demonstrate tool registry."""
    import asyncio

    print("=" * 60)
    print("BAEL Tool Registry Demo")
    print("=" * 60)

    async def run_demo():
        registry = ToolRegistry()

        # Register some tools
        print("\nRegistering tools...")

        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        async def fetch_url(url: str) -> str:
            """Fetch URL content."""
            return f"Content from {url}"

        def validate_email(email: str) -> bool:
            """Validate email format."""
            return "@" in email

        tool1 = registry.register(
            add_numbers,
            category=ToolCategory.MATH,
            description="Add two numbers together",
            tags=["math", "arithmetic"],
        )
        print(f"  Registered: {tool1.name}")

        tool2 = registry.register(
            fetch_url,
            category=ToolCategory.NETWORK,
            description="Fetch content from URL",
            tags=["network", "http"],
        )
        print(f"  Registered: {tool2.name}")

        tool3 = registry.register(
            validate_email,
            category=ToolCategory.VALIDATION,
            description="Validate email format",
            tags=["validation", "email"],
        )
        print(f"  Registered: {tool3.name}")

        # Register alias
        registry.register_alias("add", tool1.id)

        # Execute tools
        print("\nExecuting tools...")

        result = await registry.execute("add_numbers", 5, 3)
        print(f"  add_numbers(5, 3) = {result}")

        result = await registry.execute("add", 10, 20)  # Using alias
        print(f"  add(10, 20) = {result}")

        result = await registry.execute("fetch_url", "https://example.com")
        print(f"  fetch_url() = {result}")

        # Search
        print("\nSearching...")

        math_tools = registry.by_category(ToolCategory.MATH)
        print(f"  Math tools: {[t.name for t in math_tools]}")

        validation_tools = registry.by_tag("validation")
        print(f"  Validation tools: {[t.name for t in validation_tools]}")

        # List
        print("\nCategories:")
        for cat, count in registry.list_categories().items():
            if count > 0:
                print(f"  {cat.value}: {count}")

        print(f"\nStats: {registry.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
