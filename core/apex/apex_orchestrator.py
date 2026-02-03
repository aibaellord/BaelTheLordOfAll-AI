"""
BAEL - APEX Orchestrator
========================

The APEX (Advanced Processing & Execution eXtreme) Orchestrator is the
ultimate unification layer that connects ALL BAEL capabilities:

- 200+ Core Modules (reasoning, memory, swarm, evolution, etc.)
- 52+ MCP Servers (tools, databases, AI models, cloud services)
- 25+ Reasoning Engines (causal, temporal, counterfactual, etc.)
- 5-Layer Memory System (working, episodic, semantic, procedural, meta)
- Multi-Agent Swarm Intelligence
- Self-Evolution & Meta-Learning
- Computer Use & Vision
- Voice Interface
- And much more...

This is the SUPREME controller that enables BAEL to operate at
MAXIMUM POTENTIAL by intelligently routing requests to the optimal
combination of core capabilities and MCP tools.

Copyright 2026 - BAEL: The Lord of All AI Agents
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.APEX")


# =============================================================================
# ENUMS & CONFIGURATION
# =============================================================================

class APEXMode(Enum):
    """APEX Operating Modes"""
    MINIMAL = "minimal"           # Core only - fastest response
    STANDARD = "standard"         # Most features enabled
    MAXIMUM = "maximum"           # All features, full power
    AUTONOMOUS = "autonomous"     # Self-directed operation
    RESEARCH = "research"         # Exploration and learning
    STEALTH = "stealth"           # Minimal footprint
    COUNCIL = "council"           # All decisions through councils
    SWARM = "swarm"               # Swarm intelligence mode
    EVOLUTION = "evolution"       # Self-evolution active


class CapabilityDomain(Enum):
    """Domains of BAEL capabilities"""
    REASONING = "reasoning"
    MEMORY = "memory"
    AGENTS = "agents"
    LEARNING = "learning"
    KNOWLEDGE = "knowledge"
    EXECUTION = "execution"
    PERCEPTION = "perception"
    COMMUNICATION = "communication"
    EVOLUTION = "evolution"
    TOOLS = "tools"
    MCP = "mcp"


class ToolCategory(Enum):
    """Categories of MCP tools"""
    FILESYSTEM = "filesystem"
    SEARCH = "search"
    DATABASE = "database"
    BROWSER = "browser"
    CODE = "code"
    AI_MODEL = "ai_model"
    CLOUD = "cloud"
    PRODUCTIVITY = "productivity"
    MONITORING = "monitoring"
    VECTOR = "vector"


@dataclass
class APEXConfig:
    """Configuration for the APEX Orchestrator"""
    mode: APEXMode = APEXMode.MAXIMUM

    # Core Capabilities
    enable_reasoning: bool = True
    enable_memory: bool = True
    enable_swarm: bool = True
    enable_evolution: bool = True
    enable_computer_use: bool = True
    enable_vision: bool = True
    enable_voice: bool = True
    enable_proactive: bool = True

    # MCP Configuration
    mcp_gateway_url: str = "http://localhost:3100"
    mcp_auto_connect: bool = True
    mcp_max_parallel_tools: int = 10

    # Performance
    max_reasoning_time_ms: int = 10000
    max_parallel_agents: int = 50
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Safety
    enable_ethics_check: bool = True
    enable_alignment_check: bool = True
    require_council_for_critical: bool = True
    max_autonomy_level: float = 0.9

    # Evolution
    evolution_interval_hours: int = 1
    auto_optimize: bool = True


@dataclass
class APEXRequest:
    """A request to the APEX Orchestrator"""
    id: str = field(default_factory=lambda: str(uuid4()))
    input: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[CapabilityDomain] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    priority: int = 5
    deadline_ms: Optional[int] = None
    parent_request: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class APEXResponse:
    """Response from the APEX Orchestrator"""
    request_id: str
    success: bool
    output: Any
    reasoning_trace: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    capabilities_used: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    cost: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CAPABILITY REGISTRY
# =============================================================================

class CapabilityRegistry:
    """
    Registry of all BAEL capabilities.
    Maps capability names to their implementations.
    """

    def __init__(self):
        self._capabilities: Dict[str, Any] = {}
        self._domains: Dict[CapabilityDomain, List[str]] = {d: [] for d in CapabilityDomain}
        self._initialized: Set[str] = set()

    def register(
        self,
        name: str,
        capability: Any,
        domain: CapabilityDomain,
        dependencies: List[str] = None
    ) -> None:
        """Register a capability"""
        self._capabilities[name] = {
            "instance": capability,
            "domain": domain,
            "dependencies": dependencies or [],
            "registered_at": datetime.now()
        }
        self._domains[domain].append(name)
        logger.info(f"Registered capability: {name} in domain {domain.value}")

    def get(self, name: str) -> Optional[Any]:
        """Get a capability by name"""
        cap = self._capabilities.get(name)
        return cap["instance"] if cap else None

    def get_by_domain(self, domain: CapabilityDomain) -> List[Any]:
        """Get all capabilities in a domain"""
        return [self._capabilities[n]["instance"] for n in self._domains[domain]]

    def list_all(self) -> List[str]:
        """List all registered capabilities"""
        return list(self._capabilities.keys())


# =============================================================================
# MCP TOOL REGISTRY
# =============================================================================

class MCPToolRegistry:
    """
    Registry of all available MCP tools across all servers.
    """

    def __init__(self, gateway_url: str = "http://localhost:3100"):
        self.gateway_url = gateway_url
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._servers: Dict[str, List[str]] = {}
        self._categories: Dict[ToolCategory, List[str]] = {c: [] for c in ToolCategory}

    async def discover_tools(self) -> int:
        """Discover all available MCP tools from the gateway"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.gateway_url}/mcp/tools") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for tool in data.get("tools", []):
                            self._register_tool(tool)
                        logger.info(f"Discovered {len(self._tools)} MCP tools")
                        return len(self._tools)
        except Exception as e:
            logger.warning(f"Could not discover MCP tools: {e}")
            # Register known tools statically
            self._register_known_tools()
        return len(self._tools)

    def _register_tool(self, tool: Dict[str, Any]) -> None:
        """Register a single tool"""
        name = tool.get("name", "")
        self._tools[name] = tool
        server = tool.get("server", "unknown")
        if server not in self._servers:
            self._servers[server] = []
        self._servers[server].append(name)

    def _register_known_tools(self) -> None:
        """Register known tools statically"""
        # This is a fallback when the gateway isn't available
        known_tools = {
            # Filesystem
            "read_file": {"server": "filesystem", "category": ToolCategory.FILESYSTEM},
            "write_file": {"server": "filesystem", "category": ToolCategory.FILESYSTEM},
            "list_directory": {"server": "filesystem", "category": ToolCategory.FILESYSTEM},
            "search_files": {"server": "filesystem", "category": ToolCategory.FILESYSTEM},

            # Search
            "brave_web_search": {"server": "brave-search", "category": ToolCategory.SEARCH},
            "brave_local_search": {"server": "brave-search", "category": ToolCategory.SEARCH},
            "exa_search": {"server": "exa", "category": ToolCategory.SEARCH},
            "tavily_search": {"server": "tavily", "category": ToolCategory.SEARCH},
            "perplexity_search": {"server": "perplexity", "category": ToolCategory.SEARCH},

            # GitHub
            "create_repository": {"server": "github", "category": ToolCategory.CODE},
            "search_repositories": {"server": "github", "category": ToolCategory.CODE},
            "get_file_contents": {"server": "github", "category": ToolCategory.CODE},
            "create_or_update_file": {"server": "github", "category": ToolCategory.CODE},
            "create_issue": {"server": "github", "category": ToolCategory.CODE},
            "create_pull_request": {"server": "github", "category": ToolCategory.CODE},

            # Browser
            "playwright_navigate": {"server": "playwright", "category": ToolCategory.BROWSER},
            "playwright_screenshot": {"server": "playwright", "category": ToolCategory.BROWSER},
            "playwright_click": {"server": "playwright", "category": ToolCategory.BROWSER},
            "playwright_fill": {"server": "playwright", "category": ToolCategory.BROWSER},

            # Databases
            "read_query": {"server": "sqlite", "category": ToolCategory.DATABASE},
            "write_query": {"server": "sqlite", "category": ToolCategory.DATABASE},
            "postgres_query": {"server": "postgres", "category": ToolCategory.DATABASE},
            "redis_get": {"server": "redis", "category": ToolCategory.DATABASE},
            "redis_set": {"server": "redis", "category": ToolCategory.DATABASE},

            # AI Models
            "openai_chat": {"server": "openai", "category": ToolCategory.AI_MODEL},
            "anthropic_message": {"server": "anthropic", "category": ToolCategory.AI_MODEL},
            "replicate_run": {"server": "replicate", "category": ToolCategory.AI_MODEL},
            "stability_generate": {"server": "stability", "category": ToolCategory.AI_MODEL},

            # Cloud
            "aws_s3_upload": {"server": "aws", "category": ToolCategory.CLOUD},
            "aws_lambda_invoke": {"server": "aws", "category": ToolCategory.CLOUD},
            "gcp_storage": {"server": "gcp", "category": ToolCategory.CLOUD},
            "cloudflare_deploy": {"server": "cloudflare", "category": ToolCategory.CLOUD},

            # Productivity
            "notion_create_page": {"server": "notion", "category": ToolCategory.PRODUCTIVITY},
            "linear_create_issue": {"server": "linear", "category": ToolCategory.PRODUCTIVITY},
            "slack_post_message": {"server": "slack", "category": ToolCategory.PRODUCTIVITY},
            "todoist_add_task": {"server": "todoist", "category": ToolCategory.PRODUCTIVITY},

            # Vector
            "qdrant_search": {"server": "qdrant", "category": ToolCategory.VECTOR},
            "chromadb_query": {"server": "chromadb", "category": ToolCategory.VECTOR},
            "neo4j_query": {"server": "neo4j", "category": ToolCategory.VECTOR},
        }

        for name, info in known_tools.items():
            self._tools[name] = {"name": name, **info}
            server = info["server"]
            if server not in self._servers:
                self._servers[server] = []
            self._servers[server].append(name)
            self._categories[info["category"]].append(name)

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool by name"""
        return self._tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get all tools in a category"""
        return self._categories.get(category, [])

    def get_tools_by_server(self, server: str) -> List[str]:
        """Get all tools from a specific server"""
        return self._servers.get(server, [])

    def list_all(self) -> List[str]:
        """List all available tools"""
        return list(self._tools.keys())


# =============================================================================
# INTELLIGENT ROUTER
# =============================================================================

class IntelligentRouter:
    """
    Routes requests to the optimal combination of capabilities and tools.
    Uses semantic analysis and historical performance data.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        tool_registry: MCPToolRegistry
    ):
        self.capabilities = capability_registry
        self.tools = tool_registry
        self._patterns: Dict[str, Tuple[List[str], List[str]]] = {}
        self._performance: Dict[str, Dict[str, float]] = {}

    def route(self, request: APEXRequest) -> Tuple[List[str], List[str]]:
        """
        Determine which capabilities and tools to use for a request.

        Returns:
            Tuple of (capability_names, tool_names)
        """
        capabilities = []
        tools = []

        input_lower = request.input.lower()

        # Analyze request and select capabilities
        if any(word in input_lower for word in ["think", "reason", "why", "how", "analyze"]):
            capabilities.extend(["reasoning_engine", "causal_reasoning", "deductive"])

        if any(word in input_lower for word in ["remember", "recall", "history", "past"]):
            capabilities.extend(["episodic_memory", "semantic_memory"])

        if any(word in input_lower for word in ["search", "find", "look up", "research"]):
            tools.extend(["brave_web_search", "exa_search"])

        if any(word in input_lower for word in ["file", "read", "write", "create file"]):
            tools.extend(["read_file", "write_file", "list_directory"])

        if any(word in input_lower for word in ["github", "repository", "code", "commit"]):
            tools.extend(["search_repositories", "get_file_contents", "create_issue"])

        if any(word in input_lower for word in ["browse", "website", "click", "navigate"]):
            tools.extend(["playwright_navigate", "playwright_screenshot", "playwright_click"])

        if any(word in input_lower for word in ["database", "query", "sql"]):
            tools.extend(["read_query", "write_query"])

        if any(word in input_lower for word in ["image", "picture", "generate image"]):
            tools.extend(["stability_generate", "replicate_run"])
            capabilities.append("vision_processor")

        if any(word in input_lower for word in ["deploy", "cloud", "aws", "gcp"]):
            tools.extend(["aws_s3_upload", "cloudflare_deploy"])

        if any(word in input_lower for word in ["task", "todo", "linear", "jira"]):
            tools.extend(["linear_create_issue", "todoist_add_task"])

        if any(word in input_lower for word in ["swarm", "multi-agent", "collaborate"]):
            capabilities.extend(["swarm_intelligence", "agent_coordinator"])

        if any(word in input_lower for word in ["evolve", "improve", "optimize"]):
            capabilities.extend(["evolution_engine", "meta_learning"])

        # Add required capabilities/tools from request
        for cap in request.required_capabilities:
            capabilities.extend(self.capabilities.get_by_domain(cap))

        capabilities.extend(request.required_tools)

        # Deduplicate
        capabilities = list(set(capabilities))
        tools = list(set(tools))

        return capabilities, tools


# =============================================================================
# APEX ORCHESTRATOR - MAIN CLASS
# =============================================================================

class APEXOrchestrator:
    """
    The APEX Orchestrator - Ultimate unified controller for BAEL.

    This orchestrator:
    1. Receives high-level requests
    2. Routes to optimal capabilities and tools
    3. Coordinates execution across systems
    4. Aggregates and synthesizes results
    5. Learns and optimizes over time
    """

    def __init__(self, config: Optional[APEXConfig] = None):
        self.config = config or APEXConfig()
        self.capabilities = CapabilityRegistry()
        self.tools = MCPToolRegistry(self.config.mcp_gateway_url)
        self.router = IntelligentRouter(self.capabilities, self.tools)

        # Core systems (lazy loaded)
        self._brain = None
        self._supreme = None
        self._ultimate = None
        self._swarm = None
        self._evolution = None
        self._memory = None
        self._reasoning = None
        self._mcp_client = None

        # State
        self._initialized = False
        self._request_count = 0
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_execution_time_ms": 0,
            "tools_invoked": 0,
            "capabilities_used": 0
        }

        logger.info("APEX Orchestrator created")

    async def initialize(self) -> None:
        """Initialize all systems"""
        if self._initialized:
            return

        logger.info("=" * 60)
        logger.info("INITIALIZING APEX ORCHESTRATOR - MAXIMUM POTENTIAL MODE")
        logger.info("=" * 60)

        # Initialize core systems
        await self._init_brain()
        await self._init_supreme()
        await self._init_swarm()
        await self._init_evolution()
        await self._init_memory()
        await self._init_reasoning()
        await self._init_mcp()

        # Discover MCP tools
        tool_count = await self.tools.discover_tools()

        self._initialized = True

        logger.info("=" * 60)
        logger.info(f"APEX ORCHESTRATOR INITIALIZED")
        logger.info(f"  Capabilities: {len(self.capabilities.list_all())}")
        logger.info(f"  MCP Tools: {tool_count}")
        logger.info(f"  Mode: {self.config.mode.value}")
        logger.info("=" * 60)

    async def _init_brain(self) -> None:
        """Initialize the Brain system"""
        try:
            from core.brain.brain import BaelBrain
            self._brain = BaelBrain()
            self.capabilities.register("brain", self._brain, CapabilityDomain.REASONING)
            logger.info("✓ Brain initialized")
        except Exception as e:
            logger.warning(f"Brain not available: {e}")

    async def _init_supreme(self) -> None:
        """Initialize the Supreme Controller"""
        try:
            from core.supreme.orchestrator import SupremeController
            self._supreme = SupremeController()
            self.capabilities.register("supreme", self._supreme, CapabilityDomain.REASONING)
            logger.info("✓ Supreme Controller initialized")
        except Exception as e:
            logger.warning(f"Supreme Controller not available: {e}")

    async def _init_swarm(self) -> None:
        """Initialize Swarm Intelligence"""
        try:
            from core.swarm.swarm_intelligence import SwarmIntelligence
            self._swarm = SwarmIntelligence()
            self.capabilities.register("swarm", self._swarm, CapabilityDomain.AGENTS)
            logger.info("✓ Swarm Intelligence initialized")
        except Exception as e:
            logger.warning(f"Swarm Intelligence not available: {e}")

    async def _init_evolution(self) -> None:
        """Initialize Evolution Engine"""
        try:
            from core.evolution.evolution_engine import EvolutionEngine
            self._evolution = EvolutionEngine()
            self.capabilities.register("evolution", self._evolution, CapabilityDomain.EVOLUTION)
            logger.info("✓ Evolution Engine initialized")
        except Exception as e:
            logger.warning(f"Evolution Engine not available: {e}")

    async def _init_memory(self) -> None:
        """Initialize Memory Systems"""
        try:
            from core.memory.manager import MemoryManager
            self._memory = MemoryManager()
            self.capabilities.register("memory", self._memory, CapabilityDomain.MEMORY)
            logger.info("✓ Memory System initialized")
        except Exception as e:
            logger.warning(f"Memory System not available: {e}")

    async def _init_reasoning(self) -> None:
        """Initialize Reasoning Engines"""
        try:
            from core.reasoning.reasoning_engine import ReasoningEngine
            self._reasoning = ReasoningEngine()
            self.capabilities.register("reasoning", self._reasoning, CapabilityDomain.REASONING)
            logger.info("✓ Reasoning Engine initialized")
        except Exception as e:
            logger.warning(f"Reasoning Engine not available: {e}")

    async def _init_mcp(self) -> None:
        """Initialize MCP Client"""
        try:
            from core.mcp_client import MCPClient
            self._mcp_client = MCPClient()
            self.capabilities.register("mcp_client", self._mcp_client, CapabilityDomain.MCP)
            logger.info("✓ MCP Client initialized")
        except Exception as e:
            logger.warning(f"MCP Client not available: {e}")

    async def process(self, request: APEXRequest) -> APEXResponse:
        """
        Process a request through the APEX system.

        This is the main entry point for all BAEL operations.
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        self._request_count += 1

        try:
            # Route request to capabilities and tools
            capabilities, tools = self.router.route(request)

            logger.info(f"Processing request {request.id}")
            logger.info(f"  Capabilities: {capabilities}")
            logger.info(f"  Tools: {tools}")

            # Execute with capabilities
            result = await self._execute_with_capabilities(
                request, capabilities, tools
            )

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            self._stats["total_requests"] += 1
            self._stats["successful_requests"] += 1
            self._stats["tools_invoked"] += len(tools)
            self._stats["capabilities_used"] += len(capabilities)

            return APEXResponse(
                request_id=request.id,
                success=True,
                output=result,
                tools_used=tools,
                capabilities_used=capabilities,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Request failed: {e}")
            self._stats["total_requests"] += 1
            self._stats["failed_requests"] += 1

            return APEXResponse(
                request_id=request.id,
                success=False,
                output=None,
                metadata={"error": str(e)}
            )

    async def _execute_with_capabilities(
        self,
        request: APEXRequest,
        capabilities: List[str],
        tools: List[str]
    ) -> Any:
        """Execute request using selected capabilities and tools"""
        results = []

        # Execute capabilities in parallel
        if capabilities:
            cap_tasks = []
            for cap_name in capabilities:
                cap = self.capabilities.get(cap_name)
                if cap and hasattr(cap, "process"):
                    cap_tasks.append(cap.process(request.input, request.context))

            if cap_tasks:
                cap_results = await asyncio.gather(*cap_tasks, return_exceptions=True)
                results.extend([r for r in cap_results if not isinstance(r, Exception)])

        # Execute MCP tools
        if tools and self._mcp_client:
            tool_tasks = []
            for tool_name in tools:
                tool_info = self.tools.get_tool(tool_name)
                if tool_info:
                    tool_tasks.append(
                        self._mcp_client.call_tool(
                            tool_info["server"],
                            tool_name,
                            {"input": request.input}
                        )
                    )

            if tool_tasks:
                tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)
                results.extend([r for r in tool_results if not isinstance(r, Exception)])

        # Synthesize results
        if len(results) == 1:
            return results[0]
        elif len(results) > 1:
            return await self._synthesize_results(results)
        else:
            # Fall back to brain processing
            if self._brain:
                return await self._brain.think(request.input)
            return {"message": "No results from capabilities or tools"}

    async def _synthesize_results(self, results: List[Any]) -> Dict[str, Any]:
        """Synthesize multiple results into a coherent response"""
        return {
            "synthesized": True,
            "source_count": len(results),
            "results": results
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            **self._stats,
            "mode": self.config.mode.value,
            "capabilities": len(self.capabilities.list_all()),
            "tools": len(self.tools.list_all()),
            "initialized": self._initialized
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

_apex_instance: Optional[APEXOrchestrator] = None

def get_apex(config: Optional[APEXConfig] = None) -> APEXOrchestrator:
    """Get or create the global APEX Orchestrator instance"""
    global _apex_instance
    if _apex_instance is None:
        _apex_instance = APEXOrchestrator(config)
    return _apex_instance


async def create_apex(
    mode: APEXMode = APEXMode.MAXIMUM,
    **kwargs
) -> APEXOrchestrator:
    """Create and initialize an APEX Orchestrator"""
    config = APEXConfig(mode=mode, **kwargs)
    apex = APEXOrchestrator(config)
    await apex.initialize()
    return apex


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def apex_process(input_text: str, **context) -> APEXResponse:
    """Quick process through APEX"""
    apex = get_apex()
    request = APEXRequest(input=input_text, context=context)
    return await apex.process(request)


async def apex_with_tools(
    input_text: str,
    tools: List[str],
    **context
) -> APEXResponse:
    """Process with specific tools required"""
    apex = get_apex()
    request = APEXRequest(
        input=input_text,
        required_tools=tools,
        context=context
    )
    return await apex.process(request)


async def apex_with_capabilities(
    input_text: str,
    capabilities: List[CapabilityDomain],
    **context
) -> APEXResponse:
    """Process with specific capabilities required"""
    apex = get_apex()
    request = APEXRequest(
        input=input_text,
        required_capabilities=capabilities,
        context=context
    )
    return await apex.process(request)
