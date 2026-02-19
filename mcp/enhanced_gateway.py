"""
ENHANCED MCP GATEWAY
====================
Unified gateway aggregating all 52+ MCP servers into a single interface.

Features:
- Auto-discovery of available servers
- Intelligent tool routing
- Load balancing and failover
- Caching and rate limiting
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.MCPGateway")


class ServerStatus(Enum):
    """MCP server status."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class ServerTier(Enum):
    """MCP server tiers by priority."""

    INFRASTRUCTURE = 0
    ESSENTIAL = 1
    POWER = 2
    ENHANCED = 3
    AI_ML = 4
    CLOUD = 5
    PRODUCTIVITY = 6
    MONITORING = 7
    VECTOR = 8


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""

    server_id: str
    name: str
    description: str = ""
    tier: ServerTier = ServerTier.ESSENTIAL

    # Connection
    transport: str = "stdio"  # stdio, http, sse
    endpoint: str = ""
    package: str = ""

    # Capabilities
    tools: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)

    # Status
    status: ServerStatus = ServerStatus.UNKNOWN
    last_check: Optional[datetime] = None

    # Performance
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    request_count: int = 0

    # Config
    env_vars: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInfo:
    """Information about an MCP tool."""

    tool_name: str
    server_id: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)

    # Usage stats
    call_count: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class ToolCallResult:
    """Result of a tool call."""

    tool_name: str
    server_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class EnhancedMCPGateway:
    """
    Unified gateway for all MCP servers.
    Provides intelligent routing, load balancing, and failover.
    """

    def __init__(self, config_path: str = None):
        # Server registry
        self.servers: Dict[str, MCPServerInfo] = {}
        self.servers_by_tier: Dict[ServerTier, List[str]] = defaultdict(list)

        # Tool registry
        self.tools: Dict[str, ToolInfo] = {}
        self.tool_to_servers: Dict[str, List[str]] = defaultdict(list)

        # Caching
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.default_cache_ttl = timedelta(minutes=5)

        # Rate limiting
        self.rate_limits: Dict[str, int] = {}
        self.rate_counts: Dict[str, int] = defaultdict(int)
        self.rate_reset: Dict[str, datetime] = {}

        # Load config
        self.config_path = (
            config_path
            or "/Volumes/SSD320/BaelTheLordOfAll-AI/mcp/config/servers-ultimate.yaml"
        )

        # Initialize with default servers
        self._initialize_default_servers()

    def _initialize_default_servers(self) -> None:
        """Initialize default MCP server configurations."""
        # Infrastructure tier
        self._register_server(
            MCPServerInfo(
                server_id="filesystem",
                name="Filesystem",
                description="File system operations",
                tier=ServerTier.ESSENTIAL,
                transport="stdio",
                package="@modelcontextprotocol/server-filesystem",
                tools=[
                    "read_file",
                    "write_file",
                    "list_directory",
                    "create_directory",
                    "move_file",
                    "search_files",
                    "get_file_info",
                    "read_multiple_files",
                ],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="brave-search",
                name="Brave Search",
                description="Web and local search",
                tier=ServerTier.ESSENTIAL,
                transport="stdio",
                package="@modelcontextprotocol/server-brave-search",
                tools=["brave_web_search", "brave_local_search"],
                env_vars=["BRAVE_API_KEY"],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="github",
                name="GitHub",
                description="GitHub repository operations",
                tier=ServerTier.ESSENTIAL,
                transport="stdio",
                package="@modelcontextprotocol/server-github",
                tools=[
                    "create_repository",
                    "list_repositories",
                    "create_issue",
                    "list_issues",
                    "create_pull_request",
                    "search_code",
                ],
                env_vars=["GITHUB_TOKEN"],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="sqlite",
                name="SQLite",
                description="SQLite database operations",
                tier=ServerTier.ESSENTIAL,
                transport="stdio",
                package="@modelcontextprotocol/server-sqlite",
                tools=[
                    "read_query",
                    "write_query",
                    "create_table",
                    "list_tables",
                    "describe_table",
                ],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="memory",
                name="Memory",
                description="Knowledge graph memory",
                tier=ServerTier.ESSENTIAL,
                transport="stdio",
                package="@modelcontextprotocol/server-memory",
                tools=[
                    "store_memory",
                    "retrieve_memory",
                    "search_memories",
                    "delete_memory",
                ],
            )
        )

        # Power tier
        self._register_server(
            MCPServerInfo(
                server_id="puppeteer",
                name="Puppeteer",
                description="Browser automation",
                tier=ServerTier.POWER,
                transport="stdio",
                package="@modelcontextprotocol/server-puppeteer",
                tools=[
                    "puppeteer_navigate",
                    "puppeteer_screenshot",
                    "puppeteer_click",
                    "puppeteer_fill",
                    "puppeteer_evaluate",
                ],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="sequential-thinking",
                name="Sequential Thinking",
                description="Multi-step reasoning",
                tier=ServerTier.POWER,
                transport="stdio",
                package="@modelcontextprotocol/server-sequential-thinking",
                tools=["sequentialthinking"],
            )
        )

        # AI/ML tier
        self._register_server(
            MCPServerInfo(
                server_id="openai",
                name="OpenAI",
                description="OpenAI API access",
                tier=ServerTier.AI_ML,
                transport="stdio",
                package="mcp-openai",
                tools=[
                    "chat_completion",
                    "embedding",
                    "image_generation",
                    "speech_to_text",
                ],
                env_vars=["OPENAI_API_KEY"],
            )
        )

        self._register_server(
            MCPServerInfo(
                server_id="anthropic",
                name="Anthropic",
                description="Claude API access",
                tier=ServerTier.AI_ML,
                transport="stdio",
                package="mcp-anthropic",
                tools=["claude_chat", "claude_analyze"],
                env_vars=["ANTHROPIC_API_KEY"],
            )
        )

        # Cloud tier
        self._register_server(
            MCPServerInfo(
                server_id="cloudflare",
                name="Cloudflare",
                description="Cloudflare services",
                tier=ServerTier.CLOUD,
                transport="stdio",
                package="mcp-cloudflare",
                tools=["workers_deploy", "r2_upload", "kv_put", "kv_get"],
                env_vars=["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
            )
        )

        logger.info(f"Initialized {len(self.servers)} MCP servers")

    def _register_server(self, server: MCPServerInfo) -> None:
        """Register an MCP server."""
        self.servers[server.server_id] = server
        self.servers_by_tier[server.tier].append(server.server_id)

        # Register tools
        for tool_name in server.tools:
            full_name = f"{server.server_id}_{tool_name}"
            self.tools[full_name] = ToolInfo(
                tool_name=tool_name,
                server_id=server.server_id,
            )
            self.tool_to_servers[tool_name].append(server.server_id)

    def discover_servers(self) -> List[MCPServerInfo]:
        """Discover available MCP servers from config."""
        try:
            import yaml

            config_path = Path(self.config_path)
            if not config_path.exists():
                logger.warning(f"Config not found: {self.config_path}")
                return []

            with open(config_path) as f:
                config = yaml.safe_load(f)

            discovered = []
            servers_config = config.get("servers", {})

            for server_id, server_config in servers_config.items():
                if server_id not in self.servers:
                    tier_name = server_config.get("tier", "essential").upper()
                    tier = getattr(ServerTier, tier_name, ServerTier.ESSENTIAL)

                    info = MCPServerInfo(
                        server_id=server_id,
                        name=server_config.get("name", server_id),
                        description=server_config.get("description", ""),
                        tier=tier,
                        transport=server_config.get("transport", "stdio"),
                        package=server_config.get("package", ""),
                        tools=server_config.get("tools", []),
                        env_vars=list(server_config.get("env", {}).keys()),
                    )

                    self._register_server(info)
                    discovered.append(info)

            logger.info(f"Discovered {len(discovered)} additional servers")
            return discovered

        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return []

    def get_tool(self, tool_name: str) -> Optional[ToolInfo]:
        """Get tool info by name."""
        # Check exact match first
        if tool_name in self.tools:
            return self.tools[tool_name]

        # Check base tool name
        for full_name, info in self.tools.items():
            if info.tool_name == tool_name:
                return info

        return None

    def find_tool_server(self, tool_name: str) -> Optional[MCPServerInfo]:
        """Find best server for a tool."""
        servers = self.tool_to_servers.get(tool_name, [])

        if not servers:
            return None

        # Sort by tier priority, then by success rate
        candidates = [self.servers[sid] for sid in servers if sid in self.servers]
        candidates.sort(key=lambda s: (s.tier.value, -s.success_rate))

        # Return first active server
        for server in candidates:
            if server.status != ServerStatus.INACTIVE:
                return server

        return candidates[0] if candidates else None

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any] = None, use_cache: bool = True
    ) -> ToolCallResult:
        """Call an MCP tool through the gateway."""
        start_time = time.time()

        # Check cache
        if use_cache:
            cache_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
            cached = self._get_cached(cache_key)
            if cached is not None:
                return ToolCallResult(
                    tool_name=tool_name,
                    server_id="cache",
                    success=True,
                    result=cached,
                    latency_ms=0.0,
                )

        # Find server
        server = self.find_tool_server(tool_name)

        if not server:
            return ToolCallResult(
                tool_name=tool_name,
                server_id="",
                success=False,
                error=f"No server found for tool: {tool_name}",
            )

        # Check rate limit
        if not self._check_rate_limit(server.server_id):
            return ToolCallResult(
                tool_name=tool_name,
                server_id=server.server_id,
                success=False,
                error="Rate limit exceeded",
            )

        try:
            # Invoke tool (placeholder - would actually call MCP server)
            result = await self._invoke_tool(server, tool_name, arguments or {})

            latency = (time.time() - start_time) * 1000

            # Update stats
            server.request_count += 1
            server.avg_latency_ms = (server.avg_latency_ms * 0.9) + (latency * 0.1)

            # Cache result
            if use_cache:
                self._set_cached(cache_key, result)

            return ToolCallResult(
                tool_name=tool_name,
                server_id=server.server_id,
                success=True,
                result=result,
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            server.success_rate = (server.success_rate * 0.9) + 0.0

            return ToolCallResult(
                tool_name=tool_name,
                server_id=server.server_id,
                success=False,
                error=str(e),
                latency_ms=latency,
            )

    async def _invoke_tool(
        self, server: MCPServerInfo, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """Invoke a tool on an MCP server."""
        # In production, this would establish connection and call the tool
        # For now, simulate the call
        await asyncio.sleep(0.01)

        return {
            "tool": tool_name,
            "server": server.server_id,
            "arguments": arguments,
            "status": "success",
        }

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key not in self.cache:
            return None

        if key in self.cache_ttl and datetime.now() > self.cache_ttl[key]:
            del self.cache[key]
            del self.cache_ttl[key]
            return None

        return self.cache[key]

    def _set_cached(self, key: str, value: Any, ttl: timedelta = None) -> None:
        """Set cached value."""
        self.cache[key] = value
        self.cache_ttl[key] = datetime.now() + (ttl or self.default_cache_ttl)

    def _check_rate_limit(self, server_id: str) -> bool:
        """Check if within rate limit."""
        limit = self.rate_limits.get(server_id, 100)  # Default 100/min

        # Reset if needed
        reset_time = self.rate_reset.get(server_id)
        if not reset_time or datetime.now() > reset_time:
            self.rate_counts[server_id] = 0
            self.rate_reset[server_id] = datetime.now() + timedelta(minutes=1)

        # Check limit
        if self.rate_counts[server_id] >= limit:
            return False

        self.rate_counts[server_id] += 1
        return True

    def get_all_tools(self) -> List[ToolInfo]:
        """Get all available tools."""
        return list(self.tools.values())

    def get_tools_by_category(self, category: str) -> List[ToolInfo]:
        """Get tools matching a category."""
        category_lower = category.lower()
        matching = []

        for tool in self.tools.values():
            # Match by server name or tool name
            server = self.servers.get(tool.server_id)
            if server:
                if category_lower in server.name.lower():
                    matching.append(tool)
                    continue

            if category_lower in tool.tool_name.lower():
                matching.append(tool)

        return matching

    def get_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        active = sum(
            1 for s in self.servers.values() if s.status == ServerStatus.ACTIVE
        )

        return {
            "total_servers": len(self.servers),
            "active_servers": active,
            "total_tools": len(self.tools),
            "cache_size": len(self.cache),
            "servers_by_tier": {
                tier.name: len(servers)
                for tier, servers in self.servers_by_tier.items()
            },
        }


# Singleton instance
_gateway: Optional[EnhancedMCPGateway] = None


def get_mcp_gateway() -> EnhancedMCPGateway:
    """Get or create the MCP Gateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = EnhancedMCPGateway()
        _gateway.discover_servers()
    return _gateway


# Export
__all__ = [
    "ServerStatus",
    "ServerTier",
    "MCPServerInfo",
    "ToolInfo",
    "ToolCallResult",
    "EnhancedMCPGateway",
    "get_mcp_gateway",
]
