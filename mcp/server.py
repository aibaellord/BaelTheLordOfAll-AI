"""
BAEL - MCP (Model Context Protocol) Server
Enables BAEL to be used as an MCP server for external tools.

This server exposes BAEL's capabilities as MCP tools that can be
consumed by Claude, VS Code, and other MCP-compatible clients.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Import unified toolkit
try:
    from tools import UnifiedToolkit
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False

logger = logging.getLogger("BAEL.MCP")


# =============================================================================
# MCP PROTOCOL TYPES
# =============================================================================

class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type
        }


@dataclass
class MCPPrompt:
    """MCP prompt definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments or []
        }


# =============================================================================
# MCP SERVER
# =============================================================================

class BaelMCPServer:
    """BAEL MCP Server implementation."""

    def __init__(self, brain=None):
        self.brain = brain
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._prompt_handlers: Dict[str, Callable] = {}

        self._register_default_tools()
        self._register_default_prompts()
        self._register_enhanced_tools()  # New toolkit integrations

    def _register_default_tools(self) -> None:
        """Register BAEL's default tools."""

        # Think tool
        self.register_tool(
            MCPTool(
                name="bael_think",
                description="Process a task using BAEL's cognitive system with multi-persona analysis",
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "The task or question to process"
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional context for the task"
                        }
                    },
                    "required": ["input"]
                }
            ),
            self._handle_think
        )

        # Research tool
        self.register_tool(
            MCPTool(
                name="bael_research",
                description="Conduct deep research on a topic using multiple sources",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to research"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Research depth (1-5)",
                            "default": 3
                        }
                    },
                    "required": ["topic"]
                }
            ),
            self._handle_research
        )

        # Code analysis tool
        self.register_tool(
            MCPTool(
                name="bael_analyze_code",
                description="Analyze code for quality, security, and improvements",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to analyze"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language"
                        },
                        "focus": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Areas to focus on: security, performance, quality, etc."
                        }
                    },
                    "required": ["code"]
                }
            ),
            self._handle_code_analysis
        )

        # Execute code tool
        self.register_tool(
            MCPTool(
                name="bael_execute_code",
                description="Execute Python code safely",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        }
                    },
                    "required": ["code"]
                }
            ),
            self._handle_execute_code
        )

        # Memory search tool
        self.register_tool(
            MCPTool(
                name="bael_memory_search",
                description="Search BAEL's memory for relevant information",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "memory_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types: episodic, semantic, procedural, vector"
                        }
                    },
                    "required": ["query"]
                }
            ),
            self._handle_memory_search
        )

        # Spawn agent tool
        self.register_tool(
            MCPTool(
                name="bael_spawn_agent",
                description="Spawn a specialized agent for a task",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Task for the agent"
                        },
                        "persona": {
                            "type": "string",
                            "description": "Persona to use: architect, coder, security, qa, creative, research, devops"
                        }
                    },
                    "required": ["task"]
                }
            ),
            self._handle_spawn_agent
        )

        # Workflow tool
        self.register_tool(
            MCPTool(
                name="bael_run_workflow",
                description="Run a predefined workflow",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow": {
                            "type": "string",
                            "description": "Workflow: code_review, research_and_implement, full_development"
                        },
                        "task": {
                            "type": "string",
                            "description": "Task description"
                        }
                    },
                    "required": ["workflow", "task"]
                }
            ),
            self._handle_workflow
        )

    def _register_default_prompts(self) -> None:
        """Register BAEL's default prompts."""

        self.register_prompt(
            MCPPrompt(
                name="bael_architect",
                description="Get architectural guidance for a project",
                arguments=[
                    {"name": "project", "description": "Project description", "required": True}
                ]
            ),
            self._handle_architect_prompt
        )

        self.register_prompt(
            MCPPrompt(
                name="bael_code_review",
                description="Get a comprehensive code review",
                arguments=[
                    {"name": "code", "description": "Code to review", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ]
            ),
            self._handle_code_review_prompt
        )

        self.register_prompt(
            MCPPrompt(
                name="bael_explain",
                description="Get a detailed explanation of a concept",
                arguments=[
                    {"name": "topic", "description": "Topic to explain", "required": True},
                    {"name": "level", "description": "Detail level: basic, intermediate, advanced", "required": False}
                ]
            ),
            self._handle_explain_prompt
        )

    def _register_enhanced_tools(self) -> None:
        """Register enhanced tools from the unified toolkit."""
        if not TOOLKIT_AVAILABLE:
            logger.warning("Unified toolkit not available - enhanced tools disabled")
            return

        # Initialize unified toolkit
        self._unified_toolkit = UnifiedToolkit()

        # =====================================================================
        # WEB TOOLS
        # =====================================================================

        # Web Fetch Tool
        self.register_tool(
            MCPTool(
                name="bael_web_fetch",
                description="Fetch content from a URL with caching and rate limiting",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers"
                        },
                        "cache": {
                            "type": "boolean",
                            "description": "Whether to cache the result",
                            "default": True
                        }
                    },
                    "required": ["url"]
                }
            ),
            self._handle_web_fetch
        )

        # Web Search Tool
        self.register_tool(
            MCPTool(
                name="bael_web_search",
                description="Search the web using multiple search providers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "provider": {
                            "type": "string",
                            "description": "Search provider: duckduckgo, google, bing, brave",
                            "default": "duckduckgo"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            self._handle_web_search
        )

        # Web Crawl Tool
        self.register_tool(
            MCPTool(
                name="bael_web_crawl",
                description="Crawl a website following links up to a specified depth",
                input_schema={
                    "type": "object",
                    "properties": {
                        "start_url": {
                            "type": "string",
                            "description": "Starting URL for the crawl"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum crawl depth",
                            "default": 2
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum pages to crawl",
                            "default": 50
                        },
                        "same_domain": {
                            "type": "boolean",
                            "description": "Stay on same domain",
                            "default": True
                        }
                    },
                    "required": ["start_url"]
                }
            ),
            self._handle_web_crawl
        )

        # =====================================================================
        # CODE TOOLS
        # =====================================================================

        # Code Format Tool
        self.register_tool(
            MCPTool(
                name="bael_code_format",
                description="Format code with proper indentation and style",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to format"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "default": "python"
                        },
                        "style": {
                            "type": "string",
                            "description": "Formatting style",
                            "default": "pep8"
                        }
                    },
                    "required": ["code"]
                }
            ),
            self._handle_code_format
        )

        # Security Scan Tool
        self.register_tool(
            MCPTool(
                name="bael_security_scan",
                description="Scan code for security vulnerabilities",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to scan"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "default": "python"
                        }
                    },
                    "required": ["code"]
                }
            ),
            self._handle_security_scan
        )

        # Code Generate Tool
        self.register_tool(
            MCPTool(
                name="bael_code_generate",
                description="Generate code from templates or specifications",
                input_schema={
                    "type": "object",
                    "properties": {
                        "template": {
                            "type": "string",
                            "description": "Template type: class, function, api, cli, test"
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the generated code"
                        },
                        "options": {
                            "type": "object",
                            "description": "Template-specific options"
                        }
                    },
                    "required": ["template", "name"]
                }
            ),
            self._handle_code_generate
        )

        # =====================================================================
        # FILE TOOLS
        # =====================================================================

        # File Read Tool
        self.register_tool(
            MCPTool(
                name="bael_file_read",
                description="Read file contents with optional line range",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to file"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line (1-indexed)"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Ending line"
                        }
                    },
                    "required": ["path"]
                }
            ),
            self._handle_file_read
        )

        # File Write Tool
        self.register_tool(
            MCPTool(
                name="bael_file_write",
                description="Write content to a file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to file"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Append instead of overwrite",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            ),
            self._handle_file_write
        )

        # File Search Tool
        self.register_tool(
            MCPTool(
                name="bael_file_search",
                description="Search for files by name pattern or content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory to search in"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Filename pattern (glob)"
                        },
                        "content_pattern": {
                            "type": "string",
                            "description": "Content pattern (regex)"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively",
                            "default": True
                        }
                    },
                    "required": ["directory"]
                }
            ),
            self._handle_file_search
        )

        # =====================================================================
        # DATABASE TOOLS
        # =====================================================================

        # SQL Query Tool
        self.register_tool(
            MCPTool(
                name="bael_sql_query",
                description="Execute SQL queries on SQLite databases",
                input_schema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "Path to SQLite database"
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute"
                        },
                        "params": {
                            "type": "array",
                            "description": "Query parameters"
                        }
                    },
                    "required": ["database", "query"]
                }
            ),
            self._handle_sql_query
        )

        # Vector Search Tool
        self.register_tool(
            MCPTool(
                name="bael_vector_search",
                description="Search vectors by similarity",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query_vector": {
                            "type": "array",
                            "description": "Query vector for similarity search"
                        },
                        "namespace": {
                            "type": "string",
                            "description": "Vector namespace to search",
                            "default": "default"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 10
                        },
                        "metric": {
                            "type": "string",
                            "description": "Distance metric: cosine, euclidean, dot",
                            "default": "cosine"
                        }
                    },
                    "required": ["query_vector"]
                }
            ),
            self._handle_vector_search
        )

        # Document Store Tool
        self.register_tool(
            MCPTool(
                name="bael_document_store",
                description="Store and retrieve documents with JSON querying",
                input_schema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "Operation: insert, find, update, delete"
                        },
                        "collection": {
                            "type": "string",
                            "description": "Collection name"
                        },
                        "document": {
                            "type": "object",
                            "description": "Document data (for insert/update)"
                        },
                        "query": {
                            "type": "object",
                            "description": "Query filter (for find/update/delete)"
                        }
                    },
                    "required": ["operation", "collection"]
                }
            ),
            self._handle_document_store
        )

        # =====================================================================
        # AI TOOLS
        # =====================================================================

        # AI Chat Tool
        self.register_tool(
            MCPTool(
                name="bael_ai_chat",
                description="Send messages to various LLM providers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "description": "Chat messages array"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use or tier: flagship, standard, fast, cheap"
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider: openai, anthropic, groq, openrouter"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Temperature for sampling",
                            "default": 0.7
                        }
                    },
                    "required": ["messages"]
                }
            ),
            self._handle_ai_chat
        )

        # AI Summarize Tool
        self.register_tool(
            MCPTool(
                name="bael_ai_summarize",
                description="Summarize text content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to summarize"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum summary length",
                            "default": 200
                        },
                        "style": {
                            "type": "string",
                            "description": "Summary style: brief, detailed, bullets, technical",
                            "default": "brief"
                        }
                    },
                    "required": ["text"]
                }
            ),
            self._handle_ai_summarize
        )

        # AI Classify Tool
        self.register_tool(
            MCPTool(
                name="bael_ai_classify",
                description="Classify text into categories",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to classify"
                        },
                        "categories": {
                            "type": "array",
                            "description": "List of possible categories",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["text", "categories"]
                }
            ),
            self._handle_ai_classify
        )

        # AI Embeddings Tool
        self.register_tool(
            MCPTool(
                name="bael_ai_embed",
                description="Generate text embeddings",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to embed"
                        },
                        "model": {
                            "type": "string",
                            "description": "Embedding model to use"
                        }
                    },
                    "required": ["text"]
                }
            ),
            self._handle_ai_embed
        )

        # =====================================================================
        # API TOOLS
        # =====================================================================

        # REST API Tool
        self.register_tool(
            MCPTool(
                name="bael_api_request",
                description="Make REST API requests",
                input_schema={
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, PATCH, DELETE"
                        },
                        "url": {
                            "type": "string",
                            "description": "Request URL"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Request headers"
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body (for POST/PUT/PATCH)"
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters"
                        }
                    },
                    "required": ["method", "url"]
                }
            ),
            self._handle_api_request
        )

        # GraphQL Tool
        self.register_tool(
            MCPTool(
                name="bael_graphql_query",
                description="Execute GraphQL queries",
                input_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {
                            "type": "string",
                            "description": "GraphQL endpoint URL"
                        },
                        "query": {
                            "type": "string",
                            "description": "GraphQL query"
                        },
                        "variables": {
                            "type": "object",
                            "description": "Query variables"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Request headers"
                        }
                    },
                    "required": ["endpoint", "query"]
                }
            ),
            self._handle_graphql_query
        )

        logger.info(f"Registered {len(self.tools)} enhanced MCP tools")

    def register_tool(self, tool: MCPTool, handler: Callable) -> None:
        """Register a tool with its handler."""
        self.tools[tool.name] = tool
        self._tool_handlers[tool.name] = handler
        logger.debug(f"Registered MCP tool: {tool.name}")

    def register_prompt(self, prompt: MCPPrompt, handler: Callable) -> None:
        """Register a prompt with its handler."""
        self.prompts[prompt.name] = prompt
        self._prompt_handlers[prompt.name] = handler
        logger.debug(f"Registered MCP prompt: {prompt.name}")

    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource."""
        self.resources[resource.uri] = resource
        logger.debug(f"Registered MCP resource: {resource.uri}")

    # =========================================================================
    # TOOL HANDLERS
    # =========================================================================

    async def _handle_think(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle think tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        result = await self.brain.think(
            arguments["input"],
            arguments.get("context")
        )

        return {
            "response": result.get("response", ""),
            "confidence": result.get("confidence"),
            "reasoning": result.get("reasoning_summary")
        }

    async def _handle_research(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        result = await self.brain.research(
            arguments["topic"],
            depth=arguments.get("depth", 3)
        )

        return result

    async def _handle_code_analysis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code analysis tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        code = arguments["code"]
        language = arguments.get("language", "python")
        focus = arguments.get("focus", ["quality", "security"])

        analysis_prompt = f"""Analyze this {language} code focusing on {', '.join(focus)}:

```{language}
{code}
```

Provide detailed analysis including issues found, recommendations, and improvements."""

        result = await self.brain.think(analysis_prompt)

        return {
            "analysis": result.get("response", ""),
            "language": language,
            "focus_areas": focus
        }

    async def _handle_execute_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code execution tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        result = await self.brain.execute_code(
            arguments["code"],
            "python"
        )

        return result

    async def _handle_memory_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory search tool call."""
        if not self.brain or not self.brain.memory_manager:
            return {"error": "Memory not initialized"}

        results = await self.brain.memory_manager.comprehensive_search(
            arguments["query"],
            memory_types=arguments.get("memory_types"),
            limit=10
        )

        return results

    async def _handle_spawn_agent(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle spawn agent tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        result = await self.brain.spawn_agent(
            arguments["task"],
            persona_id=arguments.get("persona")
        )

        return result

    async def _handle_workflow(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow tool call."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        # This would use the orchestrator
        return {
            "workflow": arguments["workflow"],
            "task": arguments["task"],
            "status": "Workflow execution would be handled by orchestrator"
        }

    # =========================================================================
    # ENHANCED TOOL HANDLERS
    # =========================================================================

    async def _handle_web_fetch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web fetch tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("web_fetch", **arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_web_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web search tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("web_search", **arguments)
            return {"success": True, "results": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_web_crawl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web crawl tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("web_crawl", **arguments)
            return {"success": True, "pages": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_code_format(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code format tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("code_format", **arguments)
            return {"success": True, "formatted": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_security_scan(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle security scan tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("security_scan", **arguments)
            return {"success": True, "vulnerabilities": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_code_generate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generate tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("code_generate", **arguments)
            return {"success": True, "code": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_file_read(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file read tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("file_read", **arguments)
            return {"success": True, "content": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_file_write(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file write tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("file_write", **arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_file_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file search tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("file_search", **arguments)
            return {"success": True, "files": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_sql_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SQL query tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("sql_query", **arguments)
            return {"success": True, "rows": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_vector_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle vector search tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("vector_search", **arguments)
            return {"success": True, "results": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_document_store(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document store tool call."""
        try:
            operation = arguments.get("operation")
            if operation == "insert":
                result = await self._unified_toolkit.execute_tool("doc_insert", **arguments)
            elif operation == "find":
                result = await self._unified_toolkit.execute_tool("doc_find", **arguments)
            elif operation == "update":
                result = await self._unified_toolkit.execute_tool("doc_update", **arguments)
            elif operation == "delete":
                result = await self._unified_toolkit.execute_tool("doc_delete", **arguments)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_ai_chat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI chat tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("ai_chat", **arguments)
            return {"success": True, "response": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_ai_summarize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI summarize tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("ai_summarize", **arguments)
            return {"success": True, "summary": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_ai_classify(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI classify tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("ai_classify", **arguments)
            return {"success": True, "classification": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_ai_embed(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI embed tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("ai_embed", **arguments)
            return {"success": True, "embedding": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_api_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("api_request", **arguments)
            return {"success": True, "response": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_graphql_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GraphQL query tool call."""
        try:
            result = await self._unified_toolkit.execute_tool("graphql_query", **arguments)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # PROMPT HANDLERS
    # =========================================================================

    async def _handle_architect_prompt(self, arguments: Dict[str, Any]) -> str:
        """Handle architect prompt."""
        project = arguments.get("project", "")

        return f"""I am BAEL's Architect Prime. Let me provide architectural guidance for: {project}

I will analyze:
1. System requirements and constraints
2. Architectural patterns and options
3. Technology stack recommendations
4. Scalability and performance considerations
5. Security architecture
6. Integration points

Please share more details about the project for comprehensive guidance."""

    async def _handle_code_review_prompt(self, arguments: Dict[str, Any]) -> str:
        """Handle code review prompt."""
        code = arguments.get("code", "")
        language = arguments.get("language", "")

        return f"""I am BAEL's Code Master. I will review this {language} code:

```{language}
{code}
```

My review will cover:
1. Code quality and readability
2. Potential bugs and issues
3. Security vulnerabilities
4. Performance optimizations
5. Best practices compliance
6. Suggested improvements"""

    async def _handle_explain_prompt(self, arguments: Dict[str, Any]) -> str:
        """Handle explain prompt."""
        topic = arguments.get("topic", "")
        level = arguments.get("level", "intermediate")

        return f"""I am BAEL. Let me explain: {topic}

I will provide a {level}-level explanation covering:
1. Core concepts and definitions
2. How it works
3. Practical examples
4. Common use cases
5. Best practices
6. Related concepts"""

    # =========================================================================
    # MCP PROTOCOL METHODS
    # =========================================================================

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._handle_initialize(params, request_id)

            elif method == "tools/list":
                return self._handle_list_tools(request_id)

            elif method == "tools/call":
                result = await self._handle_call_tool(params)
                return self._response(request_id, result)

            elif method == "resources/list":
                return self._handle_list_resources(request_id)

            elif method == "resources/read":
                result = await self._handle_read_resource(params)
                return self._response(request_id, result)

            elif method == "prompts/list":
                return self._handle_list_prompts(request_id)

            elif method == "prompts/get":
                result = await self._handle_get_prompt(params)
                return self._response(request_id, result)

            else:
                return self._error(request_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return self._error(request_id, -32603, str(e))

    def _handle_initialize(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle initialize request."""
        return self._response(request_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "bael",
                "version": "1.0.0"
            }
        })

    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        return self._response(request_id, {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        })

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self._tool_handlers:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self._tool_handlers[tool_name]
        result = await handler(arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }

    def _handle_list_resources(self, request_id: Any) -> Dict[str, Any]:
        """Handle resources/list request."""
        return self._response(request_id, {
            "resources": [res.to_dict() for res in self.resources.values()]
        })

    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        if uri not in self.resources:
            raise ValueError(f"Unknown resource: {uri}")

        # Read resource content
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": f"Resource content for {uri}"
                }
            ]
        }

    def _handle_list_prompts(self, request_id: Any) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return self._response(request_id, {
            "prompts": [prompt.to_dict() for prompt in self.prompts.values()]
        })

    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if prompt_name not in self._prompt_handlers:
            raise ValueError(f"Unknown prompt: {prompt_name}")

        handler = self._prompt_handlers[prompt_name]
        result = await handler(arguments)

        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": result
                    }
                }
            ]
        }

    def _response(self, request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create success response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _error(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    # =========================================================================
    # STDIO TRANSPORT
    # =========================================================================

    async def run_stdio(self) -> None:
        """Run server using stdio transport."""
        import sys

        logger.info("BAEL MCP Server starting (stdio)")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin
        )

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break

                request = json.loads(line.decode())
                response = await self.handle_request(request)

                response_json = json.dumps(response) + "\n"
                writer.write(response_json.encode())
                await writer.drain()

            except Exception as e:
                logger.error(f"STDIO error: {e}")
                break

        logger.info("BAEL MCP Server stopped")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run MCP server."""
    server = BaelMCPServer()

    # For testing, just print available tools
    print("BAEL MCP Server")
    print("=" * 40)
    print("\nAvailable Tools:")
    for name, tool in server.tools.items():
        print(f"  - {name}: {tool.description}")

    print("\nAvailable Prompts:")
    for name, prompt in server.prompts.items():
        print(f"  - {name}: {prompt.description}")

    # To run as stdio server:
    # await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
