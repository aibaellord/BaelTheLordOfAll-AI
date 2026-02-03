"""
BAEL Autonomous Systems
=======================

Self-managing, self-updating, self-improving autonomous capabilities.

This package provides:
- AutoSetup: Automatic configuration of all integrations
- ServiceDiscovery: Find and integrate available services
- SelfUpdate: Keep BAEL updated with latest capabilities
- OpportunityFinder: Discover new tools and improvements
- ConfigurationManager: Centralized settings management

The goal is TRUE AUTONOMY - BAEL handles its own setup and maintenance
so you can focus on using it, not configuring it.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

__version__ = "1.0.0"


class ServiceStatus(Enum):
    """Status of a discovered service."""
    AVAILABLE = "available"        # Ready to use
    NEEDS_CONFIG = "needs_config"  # Requires API key or setup
    UNAVAILABLE = "unavailable"    # Not accessible
    UNKNOWN = "unknown"            # Not yet checked


class ConfigurationLevel(Enum):
    """How automated the configuration is."""
    FULLY_AUTO = "fully_auto"      # No user input needed
    SUGGESTED = "suggested"        # Defaults provided, user confirms
    MANUAL = "manual"              # User must provide values


@dataclass
class DiscoveredService:
    """A service that BAEL has discovered."""
    name: str
    category: str  # llm, mcp, tool, api, storage, etc.
    status: ServiceStatus = ServiceStatus.UNKNOWN
    config_level: ConfigurationLevel = ConfigurationLevel.SUGGESTED
    description: str = ""
    setup_instructions: str = ""
    auto_config: Dict[str, Any] = field(default_factory=dict)
    required_secrets: List[str] = field(default_factory=list)
    optional_secrets: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher = more important
    installed: bool = False


@dataclass
class ConfigurationSuggestion:
    """A suggested configuration change."""
    category: str
    setting: str
    current_value: Any
    suggested_value: Any
    reason: str
    impact: str  # What changes if applied
    auto_apply: bool = False  # Can be applied without confirmation


@dataclass
class OpportunityReport:
    """Report of opportunities for improvement."""
    new_services: List[DiscoveredService] = field(default_factory=list)
    config_suggestions: List[ConfigurationSuggestion] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)
    available_updates: List[Dict[str, Any]] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)


# Service catalog - all known services BAEL can integrate with
SERVICE_CATALOG = {
    # LLM Providers
    "openrouter": DiscoveredService(
        name="OpenRouter",
        category="llm",
        description="Access 100+ LLM models through one API",
        required_secrets=["OPENROUTER_API_KEY"],
        capabilities=["chat", "completion", "vision", "tools"],
        priority=10,
        setup_instructions="Get API key from https://openrouter.ai/keys"
    ),
    "anthropic": DiscoveredService(
        name="Anthropic Claude",
        category="llm",
        description="Direct access to Claude models",
        required_secrets=["ANTHROPIC_API_KEY"],
        capabilities=["chat", "completion", "vision", "extended_thinking"],
        priority=9,
        setup_instructions="Get API key from https://console.anthropic.com/"
    ),
    "openai": DiscoveredService(
        name="OpenAI",
        category="llm",
        description="GPT-4, GPT-4o, o1, and other OpenAI models",
        required_secrets=["OPENAI_API_KEY"],
        capabilities=["chat", "completion", "vision", "tools", "embeddings"],
        priority=9,
        setup_instructions="Get API key from https://platform.openai.com/"
    ),
    "ollama": DiscoveredService(
        name="Ollama (Local)",
        category="llm",
        description="Run LLMs locally - free, private, no API key needed",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["chat", "completion", "embeddings"],
        priority=10,
        setup_instructions="Install from https://ollama.ai - then 'ollama pull llama3'"
    ),
    "groq": DiscoveredService(
        name="Groq",
        category="llm",
        description="Ultra-fast inference for Llama and Mixtral",
        required_secrets=["GROQ_API_KEY"],
        capabilities=["chat", "completion"],
        priority=7,
        setup_instructions="Get API key from https://console.groq.com/"
    ),

    # MCP Servers
    "mcp_filesystem": DiscoveredService(
        name="MCP Filesystem",
        category="mcp",
        description="File system access through MCP",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["read_file", "write_file", "list_dir"],
        priority=8
    ),
    "mcp_github": DiscoveredService(
        name="MCP GitHub",
        category="mcp",
        description="GitHub integration - repos, issues, PRs",
        required_secrets=["GITHUB_TOKEN"],
        capabilities=["repo_access", "issue_management", "pr_management"],
        priority=8,
        setup_instructions="Create token at https://github.com/settings/tokens"
    ),
    "mcp_slack": DiscoveredService(
        name="MCP Slack",
        category="mcp",
        description="Slack workspace integration",
        required_secrets=["SLACK_BOT_TOKEN"],
        capabilities=["send_message", "read_channels", "manage_threads"],
        priority=6
    ),
    "mcp_postgres": DiscoveredService(
        name="MCP PostgreSQL",
        category="mcp",
        description="PostgreSQL database access",
        required_secrets=["POSTGRES_URL"],
        capabilities=["query", "schema_inspect"],
        priority=7
    ),
    "mcp_brave_search": DiscoveredService(
        name="MCP Brave Search",
        category="mcp",
        description="Web search via Brave",
        required_secrets=["BRAVE_API_KEY"],
        capabilities=["web_search"],
        priority=6
    ),

    # Tools and Services
    "playwright": DiscoveredService(
        name="Playwright Browser",
        category="tool",
        description="Browser automation and web scraping",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["browse", "screenshot", "scrape", "automate"],
        priority=8,
        setup_instructions="pip install playwright && playwright install"
    ),
    "docker": DiscoveredService(
        name="Docker",
        category="tool",
        description="Container management for sandboxed execution",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["sandbox", "containers", "isolated_execution"],
        priority=7
    ),

    # Storage
    "chromadb": DiscoveredService(
        name="ChromaDB",
        category="storage",
        description="Local vector database for embeddings",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["vector_store", "similarity_search"],
        priority=8,
        setup_instructions="pip install chromadb"
    ),
    "sqlite": DiscoveredService(
        name="SQLite",
        category="storage",
        description="Local SQL database (built-in)",
        config_level=ConfigurationLevel.FULLY_AUTO,
        capabilities=["sql", "persistence"],
        priority=10
    ),
    "redis": DiscoveredService(
        name="Redis",
        category="storage",
        description="In-memory cache and message broker",
        optional_secrets=["REDIS_URL"],
        capabilities=["cache", "pubsub", "queues"],
        priority=6
    ),
}


# Export main classes
__all__ = [
    "ServiceStatus",
    "ConfigurationLevel",
    "DiscoveredService",
    "ConfigurationSuggestion",
    "OpportunityReport",
    "SERVICE_CATALOG",
]
