"""
BAEL Tools - Comprehensive Tool System
Provides all tool capabilities for the BAEL agent system.
"""

# Import core loader components (these exist)
from .loader import (BaseTool, PythonExecutor, ShellExecutor, ToolCategory,
                     ToolLoader, ToolResult, ToolSchema)

# Try to import other toolkits (may not all exist)
try:
    from .ai import AIToolkit, EmbeddingGenerator, LLMRouter, TextSummarizer
except ImportError:
    AIToolkit = EmbeddingGenerator = LLMRouter = TextSummarizer = None

try:
    from .api import APIToolkit, GraphQLClient, RESTClient, WebhookManager
except ImportError:
    APIToolkit = GraphQLClient = RESTClient = WebhookManager = None

try:
    from .code import CodeAnalyzer, CodeExecutor, CodeFormatter, CodeToolkit
except ImportError:
    CodeAnalyzer = CodeExecutor = CodeFormatter = CodeToolkit = None

try:
    from .database import (DatabaseToolkit, DocumentStore, KeyValueStore,
                           SQLiteClient, VectorStore)
except ImportError:
    DatabaseToolkit = DocumentStore = KeyValueStore = SQLiteClient = VectorStore = None

try:
    from .file import FileReader, FileSearcher, FileToolkit, FileWriter
except ImportError:
    FileReader = FileSearcher = FileToolkit = FileWriter = None

try:
    from .web import APIClient as WebAPIClient
    from .web import WebScraper, WebSearch, WebToolkit
except ImportError:
    WebAPIClient = WebScraper = WebSearch = WebToolkit = None

__all__ = [
    # Core
    "BaseTool",
    "ToolResult",
    "ToolSchema",
    "ToolCategory",
    "ToolLoader",
    "PythonExecutor",
    "ShellExecutor",
]


class UnifiedToolkit:
    """
    Unified access to all BAEL tools.

    This is the master toolkit that provides access to all tool categories.
    """

    def __init__(self):
        # Initialize all toolkits
        self.web = WebToolkit()
        self.code = CodeToolkit()
        self.file = FileToolkit()
        self.database = DatabaseToolkit()
        self.ai = AIToolkit()
        self.api = APIToolkit()

    def get_all_tools(self):
        """Get all tool definitions from all toolkits."""
        all_tools = []

        # Gather tools from each toolkit
        if hasattr(self.web, 'get_tool_definitions'):
            all_tools.extend(self.web.get_tool_definitions())
        if hasattr(self.code, 'get_tool_definitions'):
            all_tools.extend(self.code.get_tool_definitions())
        if hasattr(self.file, 'get_tool_definitions'):
            all_tools.extend(self.file.get_tool_definitions())
        if hasattr(self.database, 'get_tool_definitions'):
            all_tools.extend(self.database.get_tool_definitions())
        if hasattr(self.ai, 'get_tool_definitions'):
            all_tools.extend(self.ai.get_tool_definitions())
        if hasattr(self.api, 'get_tool_definitions'):
            all_tools.extend(self.api.get_tool_definitions())

        return all_tools

    def get_tool_by_name(self, name: str):
        """Get a specific tool by name."""
        for tool in self.get_all_tools():
            if tool.get("name") == name:
                return tool
        return None

    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name."""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        handler = tool.get("handler")
        if not handler:
            raise ValueError(f"Tool has no handler: {tool_name}")

        # Check if async
        import asyncio
        if asyncio.iscoroutinefunction(handler):
            return await handler(**kwargs)
        else:
            return handler(**kwargs)

    def list_tools(self):
        """List all available tools."""
        tools = self.get_all_tools()
        return [
            {"name": t.get("name"), "description": t.get("description")}
            for t in tools
        ]
