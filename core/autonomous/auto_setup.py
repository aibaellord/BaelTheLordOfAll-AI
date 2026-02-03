"""
BAEL Auto-Setup Wizard
======================

Autonomous setup system that configures BAEL with zero user research required.
Discovers what's available, suggests optimal configuration, and can auto-apply.

Features:
- One-command full setup
- Interactive guided setup
- Auto-detection of all services
- Smart defaults based on environment
- Automatic MCP configuration
- API key validation
- Dependency installation
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import (SERVICE_CATALOG, ConfigurationLevel, ConfigurationSuggestion,
               DiscoveredService, OpportunityReport, ServiceStatus)
from .discovery import ServiceDiscovery, run_discovery

logger = logging.getLogger("BAEL.AutoSetup")


@dataclass
class SetupStep:
    """A step in the setup process."""
    id: str
    name: str
    description: str
    action: str  # "install", "configure", "validate", "skip"
    required: bool = False
    auto_runnable: bool = False
    command: Optional[str] = None
    config_key: Optional[str] = None
    config_value: Any = None
    completed: bool = False
    skipped: bool = False
    error: Optional[str] = None


@dataclass
class SetupPlan:
    """Complete setup plan for BAEL."""
    steps: List[SetupStep] = field(default_factory=list)
    estimated_time_minutes: int = 0
    requires_user_input: bool = False
    auto_steps: int = 0
    manual_steps: int = 0


class AutoSetup:
    """
    Autonomous setup wizard for BAEL.

    Analyzes the environment, creates an optimal setup plan,
    and can execute it automatically or interactively.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "config"
        self.secrets_dir = self.config_dir / "secrets"
        self.settings_dir = self.config_dir / "settings"

        self.discovery = ServiceDiscovery(self.config_dir)
        self.plan: Optional[SetupPlan] = None
        self.report: Optional[OpportunityReport] = None

        # Ensure directories exist
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)

    async def analyze(self) -> SetupPlan:
        """
        Analyze the environment and create a setup plan.

        Returns a SetupPlan with all steps needed to fully configure BAEL.
        """
        logger.info("Analyzing environment for setup...")

        # Run discovery
        self.report = await self.discovery.discover_all()

        # Create plan based on discovery
        self.plan = self._create_plan()

        return self.plan

    def _create_plan(self) -> SetupPlan:
        """Create a setup plan based on discovery results."""
        steps = []

        # 1. Core dependencies
        steps.append(SetupStep(
            id="deps_core",
            name="Install Core Dependencies",
            description="Install essential Python packages",
            action="install",
            required=True,
            auto_runnable=True,
            command="pip install -r requirements.txt"
        ))

        # 2. LLM Provider setup
        llm_available = any(
            s.status == ServiceStatus.AVAILABLE and s.category == "llm"
            for s in self.discovery.discovered.values()
        )

        if not llm_available:
            # Check if Ollama is installed but not running
            ollama_probe = self.discovery.probe_results.get("ollama")
            if ollama_probe and "not running" in (ollama_probe.error or ""):
                steps.append(SetupStep(
                    id="ollama_start",
                    name="Start Ollama Server",
                    description="Start the local Ollama LLM server",
                    action="install",
                    required=True,
                    auto_runnable=True,
                    command="ollama serve &"
                ))
                steps.append(SetupStep(
                    id="ollama_model",
                    name="Download Ollama Model",
                    description="Download a local LLM (llama3.2 recommended)",
                    action="install",
                    required=True,
                    auto_runnable=True,
                    command="ollama pull llama3.2"
                ))
            elif ollama_probe and "not installed" in (ollama_probe.error or ""):
                steps.append(SetupStep(
                    id="llm_choice",
                    name="Configure LLM Provider",
                    description="Set up an LLM provider. Options: Ollama (free/local), OpenRouter, Anthropic, OpenAI",
                    action="configure",
                    required=True,
                    auto_runnable=False
                ))
            else:
                # Suggest OpenRouter as it has the most models
                steps.append(SetupStep(
                    id="llm_openrouter",
                    name="Configure OpenRouter API",
                    description="Set OPENROUTER_API_KEY for access to 100+ models",
                    action="configure",
                    required=True,
                    auto_runnable=False,
                    config_key="OPENROUTER_API_KEY"
                ))

        # 3. Vector storage
        chromadb_available = (
            "chromadb" in self.discovery.discovered and
            self.discovery.discovered["chromadb"].status == ServiceStatus.AVAILABLE
        )
        if not chromadb_available:
            steps.append(SetupStep(
                id="chromadb_install",
                name="Install ChromaDB",
                description="Install local vector database for semantic search",
                action="install",
                required=False,
                auto_runnable=True,
                command="pip install chromadb"
            ))

        # 4. Browser automation
        playwright_available = (
            "playwright" in self.discovery.discovered and
            self.discovery.discovered["playwright"].status == ServiceStatus.AVAILABLE
        )
        if not playwright_available:
            steps.append(SetupStep(
                id="playwright_install",
                name="Install Playwright",
                description="Install browser automation for web tasks",
                action="install",
                required=False,
                auto_runnable=True,
                command="pip install playwright && playwright install chromium"
            ))

        # 5. MCP configuration
        steps.append(SetupStep(
            id="mcp_config",
            name="Configure MCP Servers",
            description="Set up Model Context Protocol for tool integration",
            action="configure",
            required=False,
            auto_runnable=True
        ))

        # 6. Create .env file
        env_file = self.secrets_dir / ".env"
        if not env_file.exists():
            steps.append(SetupStep(
                id="env_create",
                name="Create Environment File",
                description="Create .env file for API keys and secrets",
                action="configure",
                required=True,
                auto_runnable=True
            ))

        # 7. Validate configuration
        steps.append(SetupStep(
            id="validate",
            name="Validate Configuration",
            description="Test all connections and verify setup",
            action="validate",
            required=True,
            auto_runnable=True
        ))

        # Calculate stats
        auto_steps = sum(1 for s in steps if s.auto_runnable)
        manual_steps = len(steps) - auto_steps
        estimated_time = auto_steps * 1 + manual_steps * 3  # 1 min auto, 3 min manual

        return SetupPlan(
            steps=steps,
            estimated_time_minutes=estimated_time,
            requires_user_input=manual_steps > 0,
            auto_steps=auto_steps,
            manual_steps=manual_steps
        )

    async def run_auto_setup(self, callback: Optional[Callable[[SetupStep], None]] = None) -> bool:
        """
        Run automatic setup for all auto-runnable steps.

        Args:
            callback: Optional function called after each step

        Returns:
            True if all auto steps completed successfully
        """
        if not self.plan:
            await self.analyze()

        success = True

        for step in self.plan.steps:
            if not step.auto_runnable:
                continue

            logger.info(f"Running step: {step.name}")

            try:
                if step.action == "install" and step.command:
                    result = subprocess.run(
                        step.command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    if result.returncode == 0:
                        step.completed = True
                    else:
                        step.error = result.stderr
                        success = False

                elif step.action == "configure":
                    if step.id == "mcp_config":
                        await self._configure_mcp()
                        step.completed = True
                    elif step.id == "env_create":
                        self._create_env_template()
                        step.completed = True

                elif step.action == "validate":
                    # Re-run discovery to validate
                    self.report = await self.discovery.discover_all()
                    step.completed = True

            except Exception as e:
                step.error = str(e)
                success = False

            if callback:
                callback(step)

        return success

    async def _configure_mcp(self) -> None:
        """Configure MCP servers."""
        mcp_config_dir = self.config_dir / "mcp"
        mcp_config_dir.mkdir(parents=True, exist_ok=True)

        # Create MCP server configuration
        servers_config = {
            "mcpServers": {
                "bael": {
                    "command": "python",
                    "args": [str(self.project_root / "mcp" / "stdio_server.py")],
                    "env": {}
                },
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(self.project_root)]
                }
            }
        }

        # Add GitHub if token available
        if os.environ.get("GITHUB_TOKEN"):
            servers_config["mcpServers"]["github"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
            }

        # Write config
        with open(mcp_config_dir / "servers.json", "w") as f:
            json.dump(servers_config, f, indent=2)

        # Also create Claude Desktop config if on macOS
        if sys.platform == "darwin":
            claude_config_dir = Path.home() / "Library" / "Application Support" / "Claude"
            if claude_config_dir.exists():
                with open(claude_config_dir / "claude_desktop_config.json", "w") as f:
                    json.dump(servers_config, f, indent=2)
                logger.info("Updated Claude Desktop MCP configuration")

    def _create_env_template(self) -> None:
        """Create .env template with all possible keys."""
        env_template = """# BAEL Configuration
# Generated by AutoSetup on {date}

# =============================================================================
# LLM PROVIDERS (at least one required)
# =============================================================================

# OpenRouter - Access 100+ models (recommended)
# Get key: https://openrouter.ai/keys
OPENROUTER_API_KEY=

# Anthropic Claude - Direct access
# Get key: https://console.anthropic.com/
ANTHROPIC_API_KEY=

# OpenAI - GPT models
# Get key: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Groq - Ultra-fast inference
# Get key: https://console.groq.com/
GROQ_API_KEY=

# =============================================================================
# INTEGRATIONS (optional)
# =============================================================================

# GitHub - Repo access, issues, PRs
# Create token: https://github.com/settings/tokens
GITHUB_TOKEN=

# Brave Search - Web search
# Get key: https://brave.com/search/api/
BRAVE_API_KEY=

# =============================================================================
# STORAGE (optional)
# =============================================================================

# Redis - Caching and message queue
REDIS_URL=redis://localhost:6379

# PostgreSQL - Database
POSTGRES_URL=

# =============================================================================
# SECURITY (auto-generated if empty)
# =============================================================================

# JWT secret for API authentication
JWT_SECRET=

# API key for external access
BAEL_API_KEY=

# =============================================================================
# SETTINGS
# =============================================================================

# Default LLM provider: openrouter, anthropic, openai, ollama, groq
DEFAULT_LLM_PROVIDER=openrouter

# Default model for general tasks
DEFAULT_MODEL=anthropic/claude-3.5-sonnet

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Enable telemetry (anonymous usage stats)
TELEMETRY_ENABLED=false
""".format(date=datetime.now().strftime("%Y-%m-%d %H:%M"))

        env_file = self.secrets_dir / ".env"
        if not env_file.exists():
            with open(env_file, "w") as f:
                f.write(env_template)
            logger.info(f"Created .env template at {env_file}")

        # Also create .env.example
        example_file = self.secrets_dir / ".env.example"
        with open(example_file, "w") as f:
            f.write(env_template)

    def get_interactive_prompts(self) -> List[Dict[str, Any]]:
        """
        Get prompts for interactive setup.

        Returns a list of prompts for steps that require user input.
        """
        prompts = []

        if not self.plan:
            return prompts

        for step in self.plan.steps:
            if step.auto_runnable or step.completed or step.skipped:
                continue

            if step.config_key:
                prompts.append({
                    "step_id": step.id,
                    "type": "secret",
                    "key": step.config_key,
                    "name": step.name,
                    "description": step.description,
                    "required": step.required
                })
            elif step.id == "llm_choice":
                prompts.append({
                    "step_id": step.id,
                    "type": "choice",
                    "name": step.name,
                    "description": step.description,
                    "options": [
                        {"value": "ollama", "label": "Ollama (Free, Local)", "description": "Run LLMs locally on your machine"},
                        {"value": "openrouter", "label": "OpenRouter (Paid)", "description": "Access 100+ models via API"},
                        {"value": "anthropic", "label": "Anthropic (Paid)", "description": "Direct Claude access"},
                        {"value": "openai", "label": "OpenAI (Paid)", "description": "GPT-4 and other models"},
                    ],
                    "required": step.required
                })

        return prompts

    def apply_user_input(self, step_id: str, value: Any) -> None:
        """Apply user input for a step."""
        for step in self.plan.steps:
            if step.id == step_id:
                if step.config_key:
                    # Save to .env
                    self._set_env_value(step.config_key, value)
                step.completed = True
                break

    def _set_env_value(self, key: str, value: str) -> None:
        """Set a value in the .env file."""
        env_file = self.secrets_dir / ".env"

        if env_file.exists():
            content = env_file.read_text()
            lines = content.split("\n")
            found = False

            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    found = True
                    break

            if not found:
                lines.append(f"{key}={value}")

            env_file.write_text("\n".join(lines))
        else:
            env_file.write_text(f"{key}={value}\n")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of setup status."""
        if not self.plan:
            return {"status": "not_analyzed"}

        completed = sum(1 for s in self.plan.steps if s.completed)
        skipped = sum(1 for s in self.plan.steps if s.skipped)
        failed = sum(1 for s in self.plan.steps if s.error)
        pending = len(self.plan.steps) - completed - skipped - failed

        return {
            "status": "complete" if pending == 0 and failed == 0 else "incomplete",
            "total_steps": len(self.plan.steps),
            "completed": completed,
            "skipped": skipped,
            "failed": failed,
            "pending": pending,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": "completed" if s.completed else "skipped" if s.skipped else "failed" if s.error else "pending",
                    "error": s.error
                }
                for s in self.plan.steps
            ]
        }


async def quick_setup() -> bool:
    """
    One-command quick setup.

    Runs full automatic setup with sensible defaults.
    Returns True if setup was successful.
    """
    print("🚀 BAEL Quick Setup")
    print("=" * 50)

    setup = AutoSetup()
    plan = await setup.analyze()

    print(f"\n📋 Setup Plan: {len(plan.steps)} steps")
    print(f"   Auto: {plan.auto_steps}, Manual: {plan.manual_steps}")
    print(f"   Est. time: {plan.estimated_time_minutes} minutes")

    print("\n🔧 Running automatic setup...")

    def on_step(step: SetupStep):
        status = "✅" if step.completed else "❌" if step.error else "⏭️"
        print(f"   {status} {step.name}")
        if step.error:
            print(f"      Error: {step.error}")

    success = await setup.run_auto_setup(callback=on_step)

    # Show manual steps if any
    prompts = setup.get_interactive_prompts()
    if prompts:
        print("\n📝 Manual Configuration Required:")
        for prompt in prompts:
            print(f"   - {prompt['name']}: {prompt['description']}")

    summary = setup.get_status_summary()
    print(f"\n📊 Status: {summary['completed']}/{summary['total_steps']} complete")

    return success and summary['pending'] == 0


# CLI interface
if __name__ == "__main__":
    asyncio.run(quick_setup())
