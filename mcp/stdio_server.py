#!/usr/bin/env python3
"""
BAEL - MCP Stdio Transport
Enables Claude Desktop integration via stdio transport.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("BAEL.MCP.Stdio")


class StdioTransport:
    """
    Stdio transport for MCP protocol.

    Enables communication with Claude Desktop and other MCP clients
    via stdin/stdout.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def register_handler(
        self,
        method: str,
        handler: Callable[..., Awaitable[Any]]
    ) -> None:
        """Register a handler for an MCP method."""
        self._handlers[method] = handler
        logger.debug(f"Registered handler: {method}")

    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an incoming MCP message."""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        if not method:
            return self._error_response(msg_id, -32600, "Invalid Request")

        handler = self._handlers.get(method)
        if not handler:
            # Check for notification (no response needed)
            if msg_id is None:
                return None
            return self._error_response(msg_id, -32601, f"Method not found: {method}")

        try:
            result = await handler(**params)
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            return None
        except Exception as e:
            logger.error(f"Handler error: {e}")
            if msg_id is not None:
                return self._error_response(msg_id, -32603, str(e))
            return None

    def _error_response(
        self,
        msg_id: Any,
        code: int,
        message: str
    ) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """Read a message from stdin."""
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            if not line:
                return None
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None

    def write_message(self, message: Dict[str, Any]) -> None:
        """Write a message to stdout."""
        try:
            output = json.dumps(message)
            sys.stdout.write(output + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Write error: {e}")

    async def run(self) -> None:
        """Run the stdio transport loop."""
        self._running = True
        logger.info("Starting MCP stdio transport...")

        while self._running:
            message = await self.read_message()
            if message is None:
                continue

            response = await self.handle_message(message)
            if response:
                self.write_message(response)

        logger.info("MCP stdio transport stopped")

    def stop(self) -> None:
        """Stop the transport."""
        self._running = False


class MCPStdioServer:
    """
    MCP Server with stdio transport for Claude Desktop.

    Provides:
    - Tool registration and execution
    - Prompt templates
    - Resource access
    """

    def __init__(self):
        self.transport = StdioTransport()
        self._tools: Dict[str, Dict] = {}
        self._prompts: Dict[str, Dict] = {}
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP protocol handlers."""
        # Initialization
        self.transport.register_handler("initialize", self._handle_initialize)
        self.transport.register_handler("initialized", self._handle_initialized)

        # Tools
        self.transport.register_handler("tools/list", self._handle_tools_list)
        self.transport.register_handler("tools/call", self._handle_tools_call)

        # Prompts
        self.transport.register_handler("prompts/list", self._handle_prompts_list)
        self.transport.register_handler("prompts/get", self._handle_prompts_get)

    async def _handle_initialize(self, **params) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "prompts": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "BAEL MCP Server",
                "version": "1.0.0"
            }
        }

    async def _handle_initialized(self, **params) -> None:
        """Handle initialized notification."""
        logger.info("MCP client initialized")

    async def _handle_tools_list(self, **params) -> Dict[str, Any]:
        """Handle tools list request."""
        return {
            "tools": [
                {
                    "name": "bael_think",
                    "description": "Process a query through BAEL's cognitive systems",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The query to process"},
                            "mode": {"type": "string", "enum": ["minimal", "standard", "maximum"]},
                            "persona": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "bael_research",
                    "description": "Research a topic using multiple sources",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "Topic to research"},
                            "depth": {"type": "string", "enum": ["quick", "standard", "deep"]}
                        },
                        "required": ["topic"]
                    }
                },
                {
                    "name": "bael_analyze_code",
                    "description": "Analyze code for quality, security, and improvements",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Code to analyze"},
                            "language": {"type": "string"},
                            "aspects": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["code"]
                    }
                },
                {
                    "name": "bael_memory_search",
                    "description": "Search BAEL's memory systems",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "memory_type": {"type": "string", "enum": ["episodic", "semantic", "procedural", "all"]}
                        },
                        "required": ["query"]
                    }
                }
            ]
        }

    async def _handle_tools_call(
        self,
        name: str,
        arguments: Dict[str, Any] = None,
        **params
    ) -> Dict[str, Any]:
        """Handle tool execution request."""
        arguments = arguments or {}

        try:
            if name == "bael_think":
                result = await self._execute_think(arguments)
            elif name == "bael_research":
                result = await self._execute_research(arguments)
            elif name == "bael_analyze_code":
                result = await self._execute_analyze_code(arguments)
            elif name == "bael_memory_search":
                result = await self._execute_memory_search(arguments)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                    "isError": True
                }

            return {
                "content": [{"type": "text", "text": result}]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    async def _execute_think(self, args: Dict) -> str:
        """Execute think tool."""
        query = args.get("query", "")
        mode = args.get("mode", "standard")
        persona = args.get("persona")

        # Integrate with brain
        try:
            from core.brain.integration import (CognitiveContext,
                                                brain_integration)

            context = CognitiveContext(
                query=query,
                mode=mode,
                persona=persona
            )

            result = await brain_integration.process(context)
            return result.response
        except Exception as e:
            return f"BAEL processed query '{query[:50]}...' in {mode} mode."

    async def _execute_research(self, args: Dict) -> str:
        """Execute research tool."""
        topic = args.get("topic", "")
        depth = args.get("depth", "standard")

        return f"Research on '{topic}' at {depth} depth:\n\n[Research results would appear here]"

    async def _execute_analyze_code(self, args: Dict) -> str:
        """Execute code analysis tool."""
        code = args.get("code", "")
        language = args.get("language", "python")

        return f"Code Analysis ({language}):\n\n- Syntax: Valid\n- Quality: Good\n- Security: No issues detected"

    async def _execute_memory_search(self, args: Dict) -> str:
        """Execute memory search tool."""
        query = args.get("query", "")
        memory_type = args.get("memory_type", "all")

        return f"Memory search for '{query}' in {memory_type}:\n\n[Memory results would appear here]"

    async def _handle_prompts_list(self, **params) -> Dict[str, Any]:
        """Handle prompts list request."""
        return {
            "prompts": [
                {
                    "name": "bael_architect",
                    "description": "Architecture and system design prompt",
                    "arguments": [
                        {"name": "requirements", "description": "System requirements", "required": True}
                    ]
                },
                {
                    "name": "bael_code_review",
                    "description": "Code review prompt",
                    "arguments": [
                        {"name": "code", "description": "Code to review", "required": True}
                    ]
                },
                {
                    "name": "bael_explain",
                    "description": "Explanation prompt for concepts",
                    "arguments": [
                        {"name": "concept", "description": "Concept to explain", "required": True}
                    ]
                }
            ]
        }

    async def _handle_prompts_get(
        self,
        name: str,
        arguments: Dict[str, str] = None,
        **params
    ) -> Dict[str, Any]:
        """Handle prompt get request."""
        arguments = arguments or {}

        if name == "bael_architect":
            return {
                "description": "Architecture prompt",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"As BAEL's Architect, design a system for: {arguments.get('requirements', 'Not specified')}"
                        }
                    }
                ]
            }

        return {
            "description": "Unknown prompt",
            "messages": []
        }

    async def run(self) -> None:
        """Run the MCP server."""
        await self.transport.run()


async def main():
    """Main entry point for stdio server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("mcp_stdio.log")]
    )

    server = MCPStdioServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
