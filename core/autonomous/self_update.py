"""
BAEL Self-Update & Opportunity Discovery
=========================================

Autonomous system that keeps BAEL updated and discovers new opportunities:
- Monitors for new MCP servers and tools
- Checks for package updates
- Discovers new AI models
- Finds integration opportunities
- Suggests capability expansions
- Auto-updates when safe

This is the system that makes BAEL truly autonomous - it improves itself
without requiring manual research or intervention.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.SelfUpdate")


class UpdateType(Enum):
    """Types of updates."""
    PACKAGE = "package"       # Python package update
    MODEL = "model"           # New AI model available
    MCP_SERVER = "mcp"        # New MCP server discovered
    TOOL = "tool"             # New tool available
    INTEGRATION = "integration"  # New integration opportunity
    SECURITY = "security"     # Security patch
    FEATURE = "feature"       # New BAEL feature


class UpdatePriority(Enum):
    """Priority of updates."""
    CRITICAL = 1   # Security issues, breaking changes
    HIGH = 2       # Major improvements
    MEDIUM = 3     # Minor improvements
    LOW = 4        # Optional enhancements


@dataclass
class DiscoveredOpportunity:
    """An opportunity discovered by the system."""
    id: str
    type: UpdateType
    priority: UpdatePriority
    title: str
    description: str
    source: str  # Where it was discovered
    action: str  # What to do about it
    auto_applicable: bool = False
    command: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)
    applied: bool = False
    dismissed: bool = False


@dataclass
class ModelInfo:
    """Information about an AI model."""
    id: str
    name: str
    provider: str
    context_length: int = 0
    capabilities: List[str] = field(default_factory=list)
    pricing: Optional[Dict[str, float]] = None
    released: Optional[datetime] = None
    recommended_for: List[str] = field(default_factory=list)


class OpportunityFinder:
    """
    Discovers opportunities for BAEL improvement.

    Scans multiple sources to find:
    - New MCP servers in the ecosystem
    - New AI models from providers
    - Package updates
    - Integration opportunities
    - Community tools and extensions
    """

    # Known sources to check
    MCP_SOURCES = [
        "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md",
        "https://api.github.com/search/repositories?q=mcp-server+language:python",
        "https://api.github.com/search/repositories?q=mcp-server+language:typescript",
    ]

    MODEL_SOURCES = {
        "openrouter": "https://openrouter.ai/api/v1/models",
        "ollama": "https://ollama.ai/library",  # Web scraping needed
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".bael" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.opportunities: List[DiscoveredOpportunity] = []
        self.known_models: Set[str] = set()
        self.known_mcps: Set[str] = set()

        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached knowledge."""
        cache_file = self.cache_dir / "known_items.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    self.known_models = set(data.get("models", []))
                    self.known_mcps = set(data.get("mcps", []))
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")

    def _save_cache(self) -> None:
        """Save knowledge cache."""
        cache_file = self.cache_dir / "known_items.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({
                    "models": list(self.known_models),
                    "mcps": list(self.known_mcps),
                    "last_update": datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    async def discover_all(self) -> List[DiscoveredOpportunity]:
        """
        Run full opportunity discovery.

        Checks all sources for new opportunities.
        """
        logger.info("Starting opportunity discovery...")

        self.opportunities = []

        # Run discoveries in parallel
        await asyncio.gather(
            self._discover_new_models(),
            self._discover_mcp_servers(),
            self._discover_package_updates(),
            self._discover_integrations(),
            return_exceptions=True
        )

        # Sort by priority
        self.opportunities.sort(key=lambda x: x.priority.value)

        # Save updated cache
        self._save_cache()

        logger.info(f"Discovery complete: {len(self.opportunities)} opportunities found")
        return self.opportunities

    async def _discover_new_models(self) -> None:
        """Discover new AI models from providers."""
        try:
            import aiohttp

            # Check OpenRouter
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if api_key:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    async with session.get(
                        "https://openrouter.ai/api/v1/models",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = data.get("data", [])

                            for model in models:
                                model_id = model.get("id", "")
                                if model_id not in self.known_models:
                                    # New model discovered!
                                    self.known_models.add(model_id)

                                    # Check if it's particularly interesting
                                    context = model.get("context_length", 0)
                                    pricing = model.get("pricing", {})

                                    # Flag interesting models
                                    interesting = (
                                        context >= 100000 or  # Long context
                                        "claude" in model_id.lower() or
                                        "gpt-4" in model_id.lower() or
                                        "o1" in model_id.lower() or
                                        float(pricing.get("prompt", "1")) < 0.001  # Very cheap
                                    )

                                    if interesting:
                                        self.opportunities.append(DiscoveredOpportunity(
                                            id=f"model_{model_id}",
                                            type=UpdateType.MODEL,
                                            priority=UpdatePriority.MEDIUM,
                                            title=f"New Model: {model.get('name', model_id)}",
                                            description=f"Context: {context:,} tokens. Provider: {model_id.split('/')[0]}",
                                            source="openrouter",
                                            action=f"Add to model registry",
                                            details=model
                                        ))

            # Check Ollama for new local models
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://localhost:11434/api/tags",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = [m["name"] for m in data.get("models", [])]

                            # Suggest popular models not installed
                            recommended = ["llama3.2", "codellama", "mistral", "mixtral", "phi3"]
                            for rec in recommended:
                                if not any(rec in m for m in models):
                                    self.opportunities.append(DiscoveredOpportunity(
                                        id=f"ollama_{rec}",
                                        type=UpdateType.MODEL,
                                        priority=UpdatePriority.LOW,
                                        title=f"Recommended Ollama Model: {rec}",
                                        description=f"Popular local model not installed",
                                        source="ollama",
                                        action=f"ollama pull {rec}",
                                        auto_applicable=True,
                                        command=f"ollama pull {rec}"
                                    ))
            except:
                pass

        except ImportError:
            logger.debug("aiohttp not available for model discovery")
        except Exception as e:
            logger.warning(f"Error discovering models: {e}")

    async def _discover_mcp_servers(self) -> None:
        """Discover new MCP servers."""
        try:
            import aiohttp

            # Search GitHub for MCP servers
            async with aiohttp.ClientSession() as session:
                # Search for Python MCP servers
                async with session.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": "mcp-server language:python",
                        "sort": "updated",
                        "per_page": 20
                    },
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for repo in data.get("items", []):
                            repo_name = repo["full_name"]
                            if repo_name not in self.known_mcps:
                                self.known_mcps.add(repo_name)

                                # Only suggest repos with good engagement
                                stars = repo.get("stargazers_count", 0)
                                if stars >= 10:
                                    self.opportunities.append(DiscoveredOpportunity(
                                        id=f"mcp_{repo_name}",
                                        type=UpdateType.MCP_SERVER,
                                        priority=UpdatePriority.LOW if stars < 50 else UpdatePriority.MEDIUM,
                                        title=f"MCP Server: {repo['name']}",
                                        description=repo.get("description", "No description")[:200],
                                        source="github",
                                        action=f"Review at {repo['html_url']}",
                                        details={
                                            "url": repo["html_url"],
                                            "stars": stars,
                                            "updated": repo.get("updated_at")
                                        }
                                    ))
        except ImportError:
            logger.debug("aiohttp not available for MCP discovery")
        except Exception as e:
            logger.warning(f"Error discovering MCP servers: {e}")

    async def _discover_package_updates(self) -> None:
        """Check for Python package updates."""
        try:
            # Use pip to check for outdated packages
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                outdated = json.loads(result.stdout)

                # Priority packages that we care about
                priority_packages = {
                    "anthropic", "openai", "langchain", "chromadb",
                    "fastapi", "pydantic", "aiohttp", "rich",
                    "sentence-transformers", "torch"
                }

                for pkg in outdated:
                    name = pkg["name"]
                    current = pkg["version"]
                    latest = pkg["latest_version"]

                    if name.lower() in priority_packages:
                        self.opportunities.append(DiscoveredOpportunity(
                            id=f"pkg_{name}",
                            type=UpdateType.PACKAGE,
                            priority=UpdatePriority.MEDIUM,
                            title=f"Update {name}",
                            description=f"Current: {current} → Latest: {latest}",
                            source="pip",
                            action=f"pip install --upgrade {name}",
                            auto_applicable=True,
                            command=f"pip install --upgrade {name}"
                        ))
        except Exception as e:
            logger.warning(f"Error checking package updates: {e}")

    async def _discover_integrations(self) -> None:
        """Discover potential integration opportunities."""
        # Check for common tools/services that could be integrated

        integrations = [
            {
                "name": "Notion",
                "check": lambda: os.environ.get("NOTION_API_KEY"),
                "description": "Connect to Notion for knowledge management",
                "setup": "Get API key from https://www.notion.so/my-integrations"
            },
            {
                "name": "Linear",
                "check": lambda: os.environ.get("LINEAR_API_KEY"),
                "description": "Connect to Linear for issue tracking",
                "setup": "Get API key from Linear settings"
            },
            {
                "name": "Supabase",
                "check": lambda: os.environ.get("SUPABASE_URL"),
                "description": "Use Supabase for database and auth",
                "setup": "Create project at https://supabase.com"
            },
            {
                "name": "Pinecone",
                "check": lambda: os.environ.get("PINECONE_API_KEY"),
                "description": "Use Pinecone for scalable vector search",
                "setup": "Get API key from https://www.pinecone.io"
            },
        ]

        for integration in integrations:
            if not integration["check"]():
                self.opportunities.append(DiscoveredOpportunity(
                    id=f"integration_{integration['name'].lower()}",
                    type=UpdateType.INTEGRATION,
                    priority=UpdatePriority.LOW,
                    title=f"Integrate with {integration['name']}",
                    description=integration["description"],
                    source="integration_scan",
                    action=integration["setup"]
                ))

    def get_recommendations(self, max_items: int = 5) -> List[DiscoveredOpportunity]:
        """
        Get top recommendations.

        Returns the most important unapplied opportunities.
        """
        return [
            o for o in self.opportunities
            if not o.applied and not o.dismissed
        ][:max_items]

    async def apply_opportunity(self, opportunity_id: str) -> bool:
        """
        Apply an opportunity if possible.

        Returns True if successfully applied.
        """
        for opp in self.opportunities:
            if opp.id == opportunity_id:
                if opp.auto_applicable and opp.command:
                    try:
                        result = subprocess.run(
                            opp.command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        if result.returncode == 0:
                            opp.applied = True
                            logger.info(f"Applied opportunity: {opp.title}")
                            return True
                        else:
                            logger.error(f"Failed to apply: {result.stderr}")
                            return False
                    except Exception as e:
                        logger.error(f"Error applying opportunity: {e}")
                        return False
                else:
                    logger.warning(f"Opportunity {opportunity_id} requires manual action")
                    return False

        return False

    def dismiss_opportunity(self, opportunity_id: str) -> None:
        """Dismiss an opportunity (won't be shown again)."""
        for opp in self.opportunities:
            if opp.id == opportunity_id:
                opp.dismissed = True
                break


class SelfUpdater:
    """
    Self-update system for BAEL.

    Handles:
    - Checking for BAEL updates
    - Safe auto-updates
    - Rollback capability
    - Update scheduling
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / ".bael_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.finder = OpportunityFinder()

    async def check_for_updates(self) -> Dict[str, Any]:
        """
        Check for all types of updates.

        Returns a summary of available updates.
        """
        opportunities = await self.finder.discover_all()

        by_type = {}
        for opp in opportunities:
            type_name = opp.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append({
                "id": opp.id,
                "title": opp.title,
                "priority": opp.priority.value,
                "auto_applicable": opp.auto_applicable
            })

        return {
            "total": len(opportunities),
            "by_type": by_type,
            "recommendations": [
                {"id": o.id, "title": o.title, "action": o.action}
                for o in self.finder.get_recommendations(5)
            ]
        }

    async def auto_update(self,
                          update_packages: bool = True,
                          update_models: bool = False,
                          dry_run: bool = True) -> Dict[str, Any]:
        """
        Run automatic updates.

        Args:
            update_packages: Update Python packages
            update_models: Download new recommended models
            dry_run: If True, only report what would be done

        Returns:
            Summary of updates applied
        """
        applied = []
        skipped = []
        failed = []

        opportunities = await self.finder.discover_all()

        for opp in opportunities:
            if not opp.auto_applicable:
                skipped.append(opp.title)
                continue

            should_apply = False
            if opp.type == UpdateType.PACKAGE and update_packages:
                should_apply = True
            elif opp.type == UpdateType.MODEL and update_models:
                should_apply = True

            if should_apply:
                if dry_run:
                    applied.append(f"[DRY RUN] {opp.title}: {opp.command}")
                else:
                    success = await self.finder.apply_opportunity(opp.id)
                    if success:
                        applied.append(opp.title)
                    else:
                        failed.append(opp.title)
            else:
                skipped.append(opp.title)

        return {
            "applied": applied,
            "skipped": skipped,
            "failed": failed,
            "dry_run": dry_run
        }

    def create_backup(self, label: str = "") -> Path:
        """Create a backup before making changes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}_{label}" if label else f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # Create backup of critical files
        critical_files = [
            "requirements.txt",
            "config/settings/main.yaml",
            "config/secrets/.env",
        ]

        backup_path.mkdir(parents=True, exist_ok=True)

        for file_path in critical_files:
            src = self.project_root / file_path
            if src.exists():
                dst = backup_path / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text())

        logger.info(f"Created backup at {backup_path}")
        return backup_path


async def run_opportunity_scan() -> None:
    """Run opportunity discovery and print results."""
    print("🔍 BAEL Opportunity Discovery")
    print("=" * 50)

    finder = OpportunityFinder()
    opportunities = await finder.discover_all()

    if not opportunities:
        print("\n✅ No new opportunities found. BAEL is up to date!")
        return

    # Group by type
    by_type: Dict[str, List[DiscoveredOpportunity]] = {}
    for opp in opportunities:
        type_name = opp.type.value
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(opp)

    for type_name, opps in sorted(by_type.items()):
        print(f"\n{type_name.upper()} ({len(opps)}):")
        for opp in opps[:5]:  # Show max 5 per type
            priority_icon = {
                UpdatePriority.CRITICAL: "🔴",
                UpdatePriority.HIGH: "🟠",
                UpdatePriority.MEDIUM: "🟡",
                UpdatePriority.LOW: "🟢"
            }[opp.priority]
            auto = "⚡" if opp.auto_applicable else "👤"
            print(f"  {priority_icon} {auto} {opp.title}")
            print(f"      {opp.description[:60]}...")

    # Show recommendations
    recs = finder.get_recommendations(3)
    if recs:
        print("\n💡 Top Recommendations:")
        for rec in recs:
            print(f"  • {rec.title}")
            print(f"    Action: {rec.action}")


# CLI interface
if __name__ == "__main__":
    asyncio.run(run_opportunity_scan())
