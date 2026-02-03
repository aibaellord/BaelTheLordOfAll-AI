"""
BAEL Service Discovery
======================

Automatically discovers and probes available services, APIs, and tools.
No more manual research - BAEL finds what's available and suggests optimal setup.

Features:
- Probe local services (Ollama, Docker, Redis, etc.)
- Check API key validity
- Discover MCP servers
- Find installed Python packages
- Network service detection
- Auto-generate setup recommendations
"""

import asyncio
import json
import logging
import os
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import (SERVICE_CATALOG, ConfigurationLevel, ConfigurationSuggestion,
               DiscoveredService, OpportunityReport, ServiceStatus)

logger = logging.getLogger("BAEL.Discovery")


@dataclass
class ProbeResult:
    """Result of probing a service."""
    service_name: str
    available: bool
    response_time_ms: float = 0
    version: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ServiceDiscovery:
    """
    Autonomous service discovery engine.

    Probes the environment to find available services,
    validates API keys, and suggests optimal configuration.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.secrets_dir = self.config_dir / "secrets"
        self.discovered: Dict[str, DiscoveredService] = {}
        self.probe_results: Dict[str, ProbeResult] = {}
        self._env_cache: Dict[str, str] = {}

    async def discover_all(self) -> OpportunityReport:
        """
        Run full discovery of all available services.

        Returns an OpportunityReport with:
        - Available services
        - Configuration suggestions
        - Missing capabilities
        - Optimization opportunities
        """
        logger.info("Starting full service discovery...")

        # Load environment
        self._load_environment()

        # Probe all service categories in parallel
        await asyncio.gather(
            self._probe_llm_providers(),
            self._probe_local_services(),
            self._probe_mcp_servers(),
            self._probe_python_packages(),
            self._probe_storage_services(),
        )

        # Generate report
        report = self._generate_report()

        logger.info(f"Discovery complete: {len(self.discovered)} services found")
        return report

    def _load_environment(self) -> None:
        """Load all environment variables and .env files."""
        # System environment
        self._env_cache = dict(os.environ)

        # Load .env files
        env_files = [
            self.secrets_dir / ".env",
            self.config_dir / ".env",
            Path(".env"),
        ]

        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                self._env_cache[key.strip()] = value.strip().strip('"\'')
                except Exception as e:
                    logger.warning(f"Error loading {env_file}: {e}")

    def _has_secret(self, key: str) -> bool:
        """Check if a secret/API key is available."""
        return bool(self._env_cache.get(key))

    def _get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        return self._env_cache.get(key)

    async def _probe_llm_providers(self) -> None:
        """Probe LLM provider availability."""
        logger.debug("Probing LLM providers...")

        # OpenRouter
        if self._has_secret("OPENROUTER_API_KEY"):
            result = await self._probe_openrouter()
            self._update_service("openrouter", result)
        else:
            self._mark_needs_config("openrouter")

        # Anthropic
        if self._has_secret("ANTHROPIC_API_KEY"):
            result = await self._probe_anthropic()
            self._update_service("anthropic", result)
        else:
            self._mark_needs_config("anthropic")

        # OpenAI
        if self._has_secret("OPENAI_API_KEY"):
            result = await self._probe_openai()
            self._update_service("openai", result)
        else:
            self._mark_needs_config("openai")

        # Ollama (local - no API key needed)
        result = await self._probe_ollama()
        self._update_service("ollama", result)

        # Groq
        if self._has_secret("GROQ_API_KEY"):
            result = await self._probe_groq()
            self._update_service("groq", result)
        else:
            self._mark_needs_config("groq")

    async def _probe_openrouter(self) -> ProbeResult:
        """Probe OpenRouter API."""
        try:
            import aiohttp
            start = datetime.now()
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self._get_secret('OPENROUTER_API_KEY')}"}
                async with session.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        return ProbeResult(
                            service_name="openrouter",
                            available=True,
                            response_time_ms=elapsed,
                            details={"model_count": len(data.get("data", []))}
                        )
                    else:
                        return ProbeResult(
                            service_name="openrouter",
                            available=False,
                            error=f"HTTP {resp.status}"
                        )
        except ImportError:
            return ProbeResult(
                service_name="openrouter",
                available=False,
                error="aiohttp not installed"
            )
        except Exception as e:
            return ProbeResult(
                service_name="openrouter",
                available=False,
                error=str(e)
            )

    async def _probe_anthropic(self) -> ProbeResult:
        """Probe Anthropic API."""
        try:
            import aiohttp
            start = datetime.now()
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self._get_secret("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01"
                }
                # Just check if the API key is valid with a minimal request
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    # 200 or 400 (validation error) both mean the key is valid
                    if resp.status in [200, 400]:
                        return ProbeResult(
                            service_name="anthropic",
                            available=True,
                            response_time_ms=elapsed
                        )
                    else:
                        return ProbeResult(
                            service_name="anthropic",
                            available=False,
                            error=f"HTTP {resp.status}"
                        )
        except ImportError:
            return ProbeResult(
                service_name="anthropic",
                available=False,
                error="aiohttp not installed"
            )
        except Exception as e:
            return ProbeResult(
                service_name="anthropic",
                available=False,
                error=str(e)
            )

    async def _probe_openai(self) -> ProbeResult:
        """Probe OpenAI API."""
        try:
            import aiohttp
            start = datetime.now()
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self._get_secret('OPENAI_API_KEY')}"}
                async with session.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        return ProbeResult(
                            service_name="openai",
                            available=True,
                            response_time_ms=elapsed,
                            details={"model_count": len(data.get("data", []))}
                        )
                    else:
                        return ProbeResult(
                            service_name="openai",
                            available=False,
                            error=f"HTTP {resp.status}"
                        )
        except ImportError:
            return ProbeResult(
                service_name="openai",
                available=False,
                error="aiohttp not installed"
            )
        except Exception as e:
            return ProbeResult(
                service_name="openai",
                available=False,
                error=str(e)
            )

    async def _probe_ollama(self) -> ProbeResult:
        """Probe local Ollama installation."""
        try:
            # Check if ollama binary exists
            result = subprocess.run(
                ["which", "ollama"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode != 0:
                return ProbeResult(
                    service_name="ollama",
                    available=False,
                    error="Ollama not installed"
                )

            # Check if ollama server is running
            try:
                import aiohttp
                start = datetime.now()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:11434/api/tags",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as resp:
                        elapsed = (datetime.now() - start).total_seconds() * 1000
                        if resp.status == 200:
                            data = await resp.json()
                            models = [m["name"] for m in data.get("models", [])]
                            return ProbeResult(
                                service_name="ollama",
                                available=True,
                                response_time_ms=elapsed,
                                details={"models": models, "model_count": len(models)}
                            )
            except:
                pass

            # Ollama installed but not running
            return ProbeResult(
                service_name="ollama",
                available=False,
                error="Ollama installed but server not running. Run: ollama serve"
            )

        except Exception as e:
            return ProbeResult(
                service_name="ollama",
                available=False,
                error=str(e)
            )

    async def _probe_groq(self) -> ProbeResult:
        """Probe Groq API."""
        try:
            import aiohttp
            start = datetime.now()
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self._get_secret('GROQ_API_KEY')}"}
                async with session.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    if resp.status == 200:
                        return ProbeResult(
                            service_name="groq",
                            available=True,
                            response_time_ms=elapsed
                        )
                    else:
                        return ProbeResult(
                            service_name="groq",
                            available=False,
                            error=f"HTTP {resp.status}"
                        )
        except ImportError:
            return ProbeResult(
                service_name="groq",
                available=False,
                error="aiohttp not installed"
            )
        except Exception as e:
            return ProbeResult(
                service_name="groq",
                available=False,
                error=str(e)
            )

    async def _probe_local_services(self) -> None:
        """Probe local services like Docker, Redis, etc."""
        logger.debug("Probing local services...")

        # Docker
        result = await self._probe_docker()
        self._update_service("docker", result)

        # Redis
        result = await self._probe_redis()
        self._update_service("redis", result)

    async def _probe_docker(self) -> ProbeResult:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version
                version_result = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True
                )
                version = version_result.stdout.strip() if version_result.returncode == 0 else None
                return ProbeResult(
                    service_name="docker",
                    available=True,
                    version=version
                )
            else:
                return ProbeResult(
                    service_name="docker",
                    available=False,
                    error="Docker not running"
                )
        except FileNotFoundError:
            return ProbeResult(
                service_name="docker",
                available=False,
                error="Docker not installed"
            )
        except Exception as e:
            return ProbeResult(
                service_name="docker",
                available=False,
                error=str(e)
            )

    async def _probe_redis(self) -> ProbeResult:
        """Check if Redis is available."""
        try:
            # Try to connect to Redis
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()

            if result == 0:
                return ProbeResult(
                    service_name="redis",
                    available=True
                )
            else:
                return ProbeResult(
                    service_name="redis",
                    available=False,
                    error="Redis not running on localhost:6379"
                )
        except Exception as e:
            return ProbeResult(
                service_name="redis",
                available=False,
                error=str(e)
            )

    async def _probe_mcp_servers(self) -> None:
        """Discover available MCP servers."""
        logger.debug("Probing MCP servers...")

        # Check for common MCP server configurations
        mcp_configs = [
            Path.home() / ".config" / "claude" / "claude_desktop_config.json",
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            self.config_dir / "mcp" / "servers.json",
        ]

        discovered_mcps = []
        for config_path in mcp_configs:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                        if "mcpServers" in config:
                            for name, server_config in config["mcpServers"].items():
                                discovered_mcps.append({
                                    "name": name,
                                    "config": server_config,
                                    "source": str(config_path)
                                })
                except Exception as e:
                    logger.warning(f"Error reading MCP config {config_path}: {e}")

        # Mark filesystem MCP based on what we found
        if discovered_mcps:
            self._update_service("mcp_filesystem", ProbeResult(
                service_name="mcp_filesystem",
                available=True,
                details={"discovered_servers": discovered_mcps}
            ))

        # Check for GitHub token
        if self._has_secret("GITHUB_TOKEN"):
            self._update_service("mcp_github", ProbeResult(
                service_name="mcp_github",
                available=True
            ))
        else:
            self._mark_needs_config("mcp_github")

    async def _probe_python_packages(self) -> None:
        """Check which relevant Python packages are installed."""
        logger.debug("Checking Python packages...")

        packages_to_check = {
            "playwright": "playwright",
            "chromadb": "chromadb",
            "aiohttp": "aiohttp",
            "fastapi": "fastapi",
            "rich": "rich",
            "sentence_transformers": "sentence-transformers",
            "torch": "torch",
            "numpy": "numpy",
            "pandas": "pandas",
            "duckduckgo_search": "duckduckgo-search",
        }

        installed = []
        missing = []

        for import_name, package_name in packages_to_check.items():
            try:
                __import__(import_name)
                installed.append(package_name)
            except ImportError:
                missing.append(package_name)

        # Update playwright status
        if "playwright" in installed:
            self._update_service("playwright", ProbeResult(
                service_name="playwright",
                available=True,
                details={"installed_packages": installed}
            ))
        else:
            self._mark_needs_config("playwright")

    async def _probe_storage_services(self) -> None:
        """Check storage service availability."""
        logger.debug("Probing storage services...")

        # SQLite is always available
        self._update_service("sqlite", ProbeResult(
            service_name="sqlite",
            available=True
        ))

        # ChromaDB
        try:
            import chromadb
            self._update_service("chromadb", ProbeResult(
                service_name="chromadb",
                available=True,
                version=getattr(chromadb, "__version__", "unknown")
            ))
        except ImportError:
            self._mark_needs_config("chromadb")

    def _update_service(self, name: str, result: ProbeResult) -> None:
        """Update a service's status based on probe result."""
        self.probe_results[name] = result

        if name in SERVICE_CATALOG:
            service = SERVICE_CATALOG[name]
            service.status = ServiceStatus.AVAILABLE if result.available else ServiceStatus.UNAVAILABLE
            service.installed = result.available
            self.discovered[name] = service

    def _mark_needs_config(self, name: str) -> None:
        """Mark a service as needing configuration."""
        if name in SERVICE_CATALOG:
            service = SERVICE_CATALOG[name]
            service.status = ServiceStatus.NEEDS_CONFIG
            self.discovered[name] = service

    def _generate_report(self) -> OpportunityReport:
        """Generate an opportunity report from discovery results."""
        report = OpportunityReport()

        # New services (available but not configured)
        for name, service in self.discovered.items():
            if service.status == ServiceStatus.NEEDS_CONFIG:
                report.new_services.append(service)

        # Configuration suggestions
        suggestions = []

        # Suggest Ollama if no LLM is configured
        llm_available = any(
            s.status == ServiceStatus.AVAILABLE and s.category == "llm"
            for s in self.discovered.values()
        )
        if not llm_available and "ollama" in self.discovered:
            suggestions.append(ConfigurationSuggestion(
                category="llm",
                setting="default_provider",
                current_value=None,
                suggested_value="ollama",
                reason="No LLM provider configured. Ollama is free and runs locally.",
                impact="Enable AI capabilities without API costs",
                auto_apply=True
            ))

        # Suggest ChromaDB for vector storage
        if "chromadb" in self.discovered and self.discovered["chromadb"].status != ServiceStatus.AVAILABLE:
            suggestions.append(ConfigurationSuggestion(
                category="storage",
                setting="vector_store",
                current_value=None,
                suggested_value="chromadb",
                reason="ChromaDB provides efficient local vector storage for embeddings",
                impact="Enable semantic search and memory retrieval",
                auto_apply=False
            ))

        report.config_suggestions = suggestions

        # Missing capabilities
        if not any(s.category == "llm" and s.status == ServiceStatus.AVAILABLE for s in self.discovered.values()):
            report.missing_capabilities.append("LLM Provider - Required for AI operations")

        if not any(s.category == "storage" and "vector" in s.capabilities for s in self.discovered.values() if s.status == ServiceStatus.AVAILABLE):
            report.missing_capabilities.append("Vector Storage - Required for semantic search")

        # Optimization suggestions
        if "ollama" in self.discovered and self.discovered["ollama"].status == ServiceStatus.AVAILABLE:
            probe = self.probe_results.get("ollama")
            if probe and probe.details.get("model_count", 0) == 0:
                report.optimization_suggestions.append(
                    "Ollama is running but has no models. Run: ollama pull llama3.2"
                )

        return report

    def get_setup_commands(self) -> List[Dict[str, str]]:
        """
        Get shell commands to set up missing services.

        Returns a list of commands that can be run to set up services.
        """
        commands = []

        for name, service in self.discovered.items():
            if service.status == ServiceStatus.NEEDS_CONFIG:
                if name == "chromadb":
                    commands.append({
                        "name": "Install ChromaDB",
                        "command": "pip install chromadb",
                        "description": "Local vector database for embeddings"
                    })
                elif name == "playwright":
                    commands.append({
                        "name": "Install Playwright",
                        "command": "pip install playwright && playwright install chromium",
                        "description": "Browser automation for web tasks"
                    })
                elif name == "ollama":
                    commands.append({
                        "name": "Start Ollama",
                        "command": "ollama serve & ollama pull llama3.2",
                        "description": "Start local LLM server and download model"
                    })

        return commands

    def to_json(self) -> str:
        """Export discovery results as JSON."""
        return json.dumps({
            "discovered_services": {
                name: {
                    "name": s.name,
                    "category": s.category,
                    "status": s.status.value,
                    "capabilities": s.capabilities,
                    "installed": s.installed,
                }
                for name, s in self.discovered.items()
            },
            "probe_results": {
                name: {
                    "available": r.available,
                    "response_time_ms": r.response_time_ms,
                    "version": r.version,
                    "error": r.error,
                }
                for name, r in self.probe_results.items()
            }
        }, indent=2)


async def run_discovery() -> OpportunityReport:
    """Convenience function to run full discovery."""
    discovery = ServiceDiscovery()
    return await discovery.discover_all()


# CLI interface
if __name__ == "__main__":
    import sys

    async def main():
        print("🔍 BAEL Service Discovery")
        print("=" * 50)

        discovery = ServiceDiscovery()
        report = await discovery.discover_all()

        print("\n📊 Discovery Results:")
        print("-" * 50)

        # Group by category
        categories = {}
        for name, service in discovery.discovered.items():
            cat = service.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((name, service))

        for category, services in sorted(categories.items()):
            print(f"\n{category.upper()}:")
            for name, service in services:
                status_icon = {
                    ServiceStatus.AVAILABLE: "✅",
                    ServiceStatus.NEEDS_CONFIG: "⚙️",
                    ServiceStatus.UNAVAILABLE: "❌",
                    ServiceStatus.UNKNOWN: "❓",
                }[service.status]
                print(f"  {status_icon} {service.name}: {service.status.value}")

        if report.missing_capabilities:
            print("\n⚠️  Missing Capabilities:")
            for cap in report.missing_capabilities:
                print(f"  - {cap}")

        if report.config_suggestions:
            print("\n💡 Suggestions:")
            for suggestion in report.config_suggestions:
                print(f"  - {suggestion.reason}")

        commands = discovery.get_setup_commands()
        if commands:
            print("\n🔧 Setup Commands:")
            for cmd in commands:
                print(f"  {cmd['name']}: {cmd['command']}")

    asyncio.run(main())
