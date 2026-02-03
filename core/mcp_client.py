"""
BAEL MCP Client
===============

Client for consuming external MCP (Model Context Protocol) servers.
This allows BAEL to use tools from any MCP server, not just expose its own.

Features:
- Connect to multiple MCP servers
- Auto-discover available tools
- Execute tools from external servers
- Handle stdio and SSE transports
- Tool caching and management
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.MCPClient")


class TransportType(Enum):
    """MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: TransportType = TransportType.STDIO
    url: Optional[str] = None  # For SSE transport
    auto_connect: bool = True
    timeout: int = 30


@dataclass
class MCPTool:
    """A tool from an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": f"{self.server_name}__{self.name}",
                "description": self.description,
                "parameters": self.input_schema
            }
        }


@dataclass
class MCPResource:
    """A resource from an MCP server."""
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None
    server_name: str = ""


@dataclass
class MCPPrompt:
    """A prompt from an MCP server."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    server_name: str = ""


class MCPConnection:
    """
    Connection to a single MCP server.

    Handles the stdio communication with the server process.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.tools: List[MCPTool] = []
        self.resources: List[MCPResource] = []
        self.prompts: List[MCPPrompt] = []
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._connected = False
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """Connect to the MCP server."""
        logger.info(f"Connecting to MCP server: {self.config.name}")

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.env)

            # Expand environment variables in env values
            for key, value in env.items():
                if value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    env[key] = os.environ.get(var_name, "")

            # Start the server process
            self.process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1
            )

            # Start reader task
            self._reader_task = asyncio.create_task(self._read_responses())

            # Initialize the connection
            await self._initialize()

            # Get capabilities
            await self._list_tools()
            await self._list_resources()
            await self._list_prompts()

            self._connected = True
            logger.info(f"Connected to {self.config.name}: {len(self.tools)} tools, {len(self.resources)} resources")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._reader_task:
            self._reader_task.cancel()

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self._connected = False
        logger.info(f"Disconnected from {self.config.name}")

    async def _read_responses(self) -> None:
        """Read responses from the server."""
        try:
            while True:
                if not self.process or not self.process.stdout:
                    break

                # Read line (blocking, so we use thread)
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stdout.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {self.config.name}: {line[:100]}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Reader error for {self.config.name}: {e}")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a message from the server."""
        msg_id = message.get("id")

        if msg_id is not None and msg_id in self._pending:
            future = self._pending.pop(msg_id)
            if "error" in message:
                future.set_exception(Exception(message["error"].get("message", "Unknown error")))
            else:
                future.set_result(message.get("result"))

    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Send a JSON-RPC request and wait for response."""
        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        # Send request
        if self.process and self.process.stdin:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
        else:
            raise Exception("Process not running")

        # Wait for response
        try:
            return await asyncio.wait_for(future, timeout=self.config.timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise Exception(f"Timeout waiting for response from {self.config.name}")

    async def _initialize(self) -> None:
        """Send initialize request."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "BAEL",
                "version": "2.0.0"
            }
        })

        # Send initialized notification
        if self.process and self.process.stdin:
            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            self.process.stdin.write(json.dumps(notification) + "\n")
            self.process.stdin.flush()

    async def _list_tools(self) -> None:
        """Get list of available tools."""
        try:
            result = await self._send_request("tools/list")
            self.tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                    server_name=self.config.name
                )
                for tool in result.get("tools", [])
            ]
        except Exception as e:
            logger.warning(f"Failed to list tools from {self.config.name}: {e}")

    async def _list_resources(self) -> None:
        """Get list of available resources."""
        try:
            result = await self._send_request("resources/list")
            self.resources = [
                MCPResource(
                    uri=res["uri"],
                    name=res.get("name", res["uri"]),
                    description=res.get("description", ""),
                    mime_type=res.get("mimeType"),
                    server_name=self.config.name
                )
                for res in result.get("resources", [])
            ]
        except Exception as e:
            # Resources may not be supported
            logger.debug(f"No resources from {self.config.name}: {e}")

    async def _list_prompts(self) -> None:
        """Get list of available prompts."""
        try:
            result = await self._send_request("prompts/list")
            self.prompts = [
                MCPPrompt(
                    name=prompt["name"],
                    description=prompt.get("description", ""),
                    arguments=prompt.get("arguments", []),
                    server_name=self.config.name
                )
                for prompt in result.get("prompts", [])
            ]
        except Exception as e:
            # Prompts may not be supported
            logger.debug(f"No prompts from {self.config.name}: {e}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on this server."""
        if not self._connected:
            raise Exception(f"Not connected to {self.config.name}")

        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        return result

    async def read_resource(self, uri: str) -> Any:
        """Read a resource from this server."""
        if not self._connected:
            raise Exception(f"Not connected to {self.config.name}")

        result = await self._send_request("resources/read", {
            "uri": uri
        })

        return result

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Get a prompt from this server."""
        if not self._connected:
            raise Exception(f"Not connected to {self.config.name}")

        result = await self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })

        return result


class MCPClient:
    """
    Client for managing multiple MCP server connections.

    Provides unified access to tools from all connected servers.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.connections: Dict[str, MCPConnection] = {}
        self._tool_index: Dict[str, MCPTool] = {}

    def load_config(self, config_path: Optional[Path] = None) -> List[MCPServerConfig]:
        """Load MCP server configurations from file."""
        path = config_path or self.config_path

        if not path:
            # Try default locations
            possible_paths = [
                Path("config/mcp/servers.json"),
                Path.home() / ".bael" / "mcp_servers.json",
                Path.home() / ".config" / "claude" / "claude_desktop_config.json",
            ]
            for p in possible_paths:
                if p.exists():
                    path = p
                    break

        if not path or not path.exists():
            logger.warning("No MCP config file found")
            return []

        configs = []

        try:
            with open(path) as f:
                data = json.load(f)

            servers = data.get("mcpServers", data.get("servers", {}))

            for name, config in servers.items():
                configs.append(MCPServerConfig(
                    name=name,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                ))

            logger.info(f"Loaded {len(configs)} MCP server configs from {path}")

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

        return configs

    async def connect_all(self, configs: Optional[List[MCPServerConfig]] = None) -> int:
        """
        Connect to all configured MCP servers.

        Returns the number of successful connections.
        """
        if configs is None:
            configs = self.load_config()

        connected = 0

        for config in configs:
            if config.auto_connect:
                success = await self.connect(config)
                if success:
                    connected += 1

        # Build tool index
        self._build_tool_index()

        logger.info(f"Connected to {connected}/{len(configs)} MCP servers")
        return connected

    async def connect(self, config: MCPServerConfig) -> bool:
        """Connect to a specific MCP server."""
        connection = MCPConnection(config)
        success = await connection.connect()

        if success:
            self.connections[config.name] = connection
            self._build_tool_index()

        return success

    async def disconnect(self, name: str) -> None:
        """Disconnect from a specific server."""
        if name in self.connections:
            await self.connections[name].disconnect()
            del self.connections[name]
            self._build_tool_index()

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for name in list(self.connections.keys()):
            await self.disconnect(name)

    def _build_tool_index(self) -> None:
        """Build index of all available tools."""
        self._tool_index.clear()

        for name, conn in self.connections.items():
            for tool in conn.tools:
                # Use qualified name to avoid conflicts
                qualified_name = f"{name}__{tool.name}"
                self._tool_index[qualified_name] = tool

    def get_all_tools(self) -> List[MCPTool]:
        """Get all available tools from all servers."""
        return list(self._tool_index.values())

    def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        return [tool.to_openai_format() for tool in self._tool_index.values()]

    def get_tool(self, qualified_name: str) -> Optional[MCPTool]:
        """Get a specific tool by qualified name."""
        return self._tool_index.get(qualified_name)

    async def call_tool(
        self,
        qualified_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool by its qualified name.

        The qualified name is in the format: server_name__tool_name
        """
        tool = self._tool_index.get(qualified_name)
        if not tool:
            raise ValueError(f"Unknown tool: {qualified_name}")

        connection = self.connections.get(tool.server_name)
        if not connection:
            raise ValueError(f"Not connected to server: {tool.server_name}")

        return await connection.call_tool(tool.name, arguments)

    def get_all_resources(self) -> List[MCPResource]:
        """Get all resources from all servers."""
        resources = []
        for conn in self.connections.values():
            resources.extend(conn.resources)
        return resources

    def get_all_prompts(self) -> List[MCPPrompt]:
        """Get all prompts from all servers."""
        prompts = []
        for conn in self.connections.values():
            prompts.extend(conn.prompts)
        return prompts

    def get_status(self) -> Dict[str, Any]:
        """Get status of all connections."""
        return {
            "connections": {
                name: {
                    "connected": conn._connected,
                    "tools": len(conn.tools),
                    "resources": len(conn.resources),
                    "prompts": len(conn.prompts),
                }
                for name, conn in self.connections.items()
            },
            "total_tools": len(self._tool_index),
        }


# Singleton client
_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client."""
    global _client
    if _client is None:
        _client = MCPClient()
        await _client.connect_all()
    return _client


async def call_mcp_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Convenience function to call an MCP tool."""
    client = await get_mcp_client()
    return await client.call_tool(name, arguments)


# CLI test
if __name__ == "__main__":
    async def test():
        print("🔌 MCP Client Test")
        print("=" * 50)

        client = MCPClient()
        configs = client.load_config()

        print(f"\nFound {len(configs)} server configurations")

        if configs:
            connected = await client.connect_all(configs)
            print(f"Connected to {connected} servers")

            tools = client.get_all_tools()
            print(f"\nAvailable tools ({len(tools)}):")
            for tool in tools[:10]:
                print(f"  - {tool.server_name}__{tool.name}: {tool.description[:50]}...")

            await client.disconnect_all()
        else:
            print("No MCP servers configured. Create config/mcp/servers.json")

    asyncio.run(test())
