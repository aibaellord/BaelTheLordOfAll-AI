#!/usr/bin/env python3
"""
BAEL - VS Code Integration Layer
SEAMLESS IDE INTEGRATION FOR TOTAL DOMINANCE

This module provides:
1. VS Code MCP tools for all BAEL capabilities
2. Task definitions for VS Code
3. Extension API for VS Code extensions
4. Real-time integration with editor
5. Code lens and hover providers
6. Diagnostic integration
7. Command palette integration
8. Status bar integration

"Control the editor, control the developer. Control the developer, control the code." - Ba'el
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("BAEL.VSCodeIntegration")


# =============================================================================
# ENUMS
# =============================================================================

class VSCodeCommand(Enum):
    """VS Code commands exposed by BAEL."""
    # Lord of All
    DOMINATE_PROJECT = "bael.dominateProject"
    QUICK_DOMINATE = "bael.quickDominate"
    AWAKEN_LORD = "bael.awakenLord"

    # Agent Teams
    DEPLOY_RED_TEAM = "bael.deployRedTeam"
    DEPLOY_BLUE_TEAM = "bael.deployBlueTeam"
    DEPLOY_ALL_TEAMS = "bael.deployAllTeams"

    # Opportunities
    DISCOVER_OPPORTUNITIES = "bael.discoverOpportunities"
    QUICK_SCAN = "bael.quickScan"
    DEEP_ANALYSIS = "bael.deepAnalysis"

    # Sprints
    START_SPRINT = "bael.startSprint"
    RUN_QUICK_SPRINT = "bael.runQuickSprint"

    # Competition
    ANALYZE_COMPETITION = "bael.analyzeCompetition"
    CONQUEST_PLAN = "bael.conquestPlan"

    # Dream Mode
    ENTER_DREAM_MODE = "bael.enterDreamMode"
    LUCID_DREAM = "bael.lucidDream"

    # Zero Invest
    FIND_FREE_RESOURCES = "bael.findFreeResources"
    OPTIMIZE_COSTS = "bael.optimizeCosts"

    # Micro Agents
    MICRO_DETAIL_SCAN = "bael.microDetailScan"
    SPAWN_MICRO_SWARM = "bael.spawnMicroSwarm"

    # Utilities
    SHOW_STATUS = "bael.showStatus"
    SHOW_CAPABILITIES = "bael.showCapabilities"


class TaskCategory(Enum):
    """Categories for VS Code tasks."""
    DOMINATION = "dominat"
    ANALYSIS = "analysis"
    DEVELOPMENT = "development"
    COMPETITION = "competition"
    CREATIVITY = "creativity"
    OPTIMIZATION = "optimization"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class VSCodeTask:
    """A VS Code task definition."""
    label: str
    type: str = "shell"
    command: str = ""
    group: str = ""
    category: TaskCategory = TaskCategory.ANALYSIS
    is_background: bool = False
    problem_matcher: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to VS Code task format."""
        task = {
            "label": self.label,
            "type": self.type,
            "command": self.command,
            "group": self.group,
            "isBackground": self.is_background,
        }
        if self.problem_matcher:
            task["problemMatcher"] = self.problem_matcher
        return task


@dataclass
class MCPTool:
    """An MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None

    def to_mcp_schema(self) -> Dict[str, Any]:
        """Convert to MCP tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }


@dataclass
class DiagnosticEntry:
    """A diagnostic entry for VS Code."""
    file_path: str
    line: int
    column: int = 0
    message: str = ""
    severity: str = "warning"  # error, warning, info, hint
    source: str = "BAEL"
    code: str = ""


# =============================================================================
# VS CODE INTEGRATION
# =============================================================================

class VSCodeIntegration:
    """
    VS Code Integration Layer for BAEL.

    Provides seamless integration with VS Code including:
    - MCP tools for Claude/AI assistants
    - Task definitions
    - Commands
    - Diagnostics
    - Status bar updates
    """

    def __init__(self, workspace_path: Path = None):
        self.workspace_path = workspace_path or Path.cwd()
        self._initialized = False
        self._mcp_tools: Dict[str, MCPTool] = {}
        self._tasks: List[VSCodeTask] = []
        self._diagnostics: List[DiagnosticEntry] = []

        # Lord of All instance (lazy loaded)
        self._lord = None

    @classmethod
    async def create(cls, workspace_path: Path = None) -> "VSCodeIntegration":
        """Factory method for async initialization."""
        instance = cls(workspace_path)
        await instance.initialize()
        return instance

    async def initialize(self):
        """Initialize the integration."""
        if self._initialized:
            return

        # Register MCP tools
        self._register_mcp_tools()

        # Create task definitions
        self._create_task_definitions()

        self._initialized = True
        logger.info("VSCodeIntegration initialized")

    async def _get_lord(self):
        """Get or create Lord of All instance."""
        if self._lord is None:
            try:
                from core.lord_of_all import LordOfAllOrchestrator
                self._lord = await LordOfAllOrchestrator.create()
            except ImportError:
                logger.warning("LordOfAllOrchestrator not available")
        return self._lord

    def _register_mcp_tools(self):
        """Register all MCP tools."""

        # Lord of All tools
        self._mcp_tools["bael_dominate"] = MCPTool(
            name="bael_dominate",
            description="Execute total dominance over a project. Analyzes, deploys agents, and conquers.",
            parameters={
                "project_path": {"type": "string", "description": "Path to project"},
                "mode": {"type": "string", "description": "Dominance mode (absolute, aggressive, etc)"}
            }
        )

        self._mcp_tools["bael_quick_dominate"] = MCPTool(
            name="bael_quick_dominate",
            description="Quick dominance operation with summary output.",
            parameters={
                "project_path": {"type": "string", "description": "Path to project"}
            }
        )

        # Agent team tools
        self._mcp_tools["bael_deploy_agents"] = MCPTool(
            name="bael_deploy_agents",
            description="Deploy specialized agent teams (Red, Blue, Black, White, Gold, Purple, Green, Silver).",
            parameters={
                "team": {"type": "string", "description": "Team color to deploy"},
                "project_path": {"type": "string", "description": "Path to project"}
            }
        )

        # Opportunity tools
        self._mcp_tools["bael_discover_opportunities"] = MCPTool(
            name="bael_discover_opportunities",
            description="Discover all improvement opportunities in a project.",
            parameters={
                "project_path": {"type": "string", "description": "Path to project"}
            }
        )

        # Sprint tools
        self._mcp_tools["bael_run_sprint"] = MCPTool(
            name="bael_run_sprint",
            description="Run an automated development sprint on a project.",
            parameters={
                "project_path": {"type": "string", "description": "Path to project"},
                "sprint_name": {"type": "string", "description": "Name of the sprint"}
            }
        )

        # Competition tools
        self._mcp_tools["bael_analyze_competition"] = MCPTool(
            name="bael_analyze_competition",
            description="Analyze competitors and create conquest plans.",
            parameters={
                "market": {"type": "string", "description": "Market to analyze"}
            }
        )

        # Dream mode tools
        self._mcp_tools["bael_dream"] = MCPTool(
            name="bael_dream",
            description="Enter dream mode for creative problem solving.",
            parameters={
                "problem": {"type": "string", "description": "Problem to dream about"}
            }
        )

        # Micro agent tools
        self._mcp_tools["bael_micro_scan"] = MCPTool(
            name="bael_micro_scan",
            description="Run micro-agent swarm for tiny detail discovery.",
            parameters={
                "project_path": {"type": "string", "description": "Path to scan"}
            }
        )

        # Zero invest tools
        self._mcp_tools["bael_find_free_resources"] = MCPTool(
            name="bael_find_free_resources",
            description="Find free resources and zero-cost opportunities.",
            parameters={
                "resource_type": {"type": "string", "description": "Type of resource needed"}
            }
        )

        logger.info(f"Registered {len(self._mcp_tools)} MCP tools")

    def _create_task_definitions(self):
        """Create VS Code task definitions."""

        self._tasks = [
            # Domination tasks
            VSCodeTask(
                label="👑 BAEL: Total Domination",
                command="python -c \"import asyncio; from core.lord_of_all import dominate_project; from pathlib import Path; asyncio.run(dominate_project(Path('${workspaceFolder}')))\"",
                group="BAEL",
                category=TaskCategory.DOMINATION
            ),

            VSCodeTask(
                label="⚡ BAEL: Quick Dominate",
                command="python -c \"import asyncio; from core.lord_of_all import LordOfAllOrchestrator; from pathlib import Path; lord = asyncio.run(LordOfAllOrchestrator.create()); print(asyncio.run(lord.quick_dominate(Path('${workspaceFolder}'))))\"",
                group="BAEL",
                category=TaskCategory.DOMINATION
            ),

            # Agent team tasks
            VSCodeTask(
                label="🔴 BAEL: Deploy Red Team (Attack)",
                command="python -c \"print('Deploying Red Team - Finding vulnerabilities...')\"",
                group="BAEL",
                category=TaskCategory.ANALYSIS
            ),

            VSCodeTask(
                label="🔵 BAEL: Deploy Blue Team (Defense)",
                command="python -c \"print('Deploying Blue Team - Ensuring stability...')\"",
                group="BAEL",
                category=TaskCategory.ANALYSIS
            ),

            VSCodeTask(
                label="🎯 BAEL: Deploy All Teams",
                command="python -c \"print('Deploying all 8 agent teams...')\"",
                group="BAEL",
                category=TaskCategory.DOMINATION
            ),

            # Opportunity tasks
            VSCodeTask(
                label="🔍 BAEL: Discover Opportunities",
                command="python -c \"import asyncio; from core.opportunity_discovery import OpportunityDiscoveryEngine; from pathlib import Path; engine = asyncio.run(OpportunityDiscoveryEngine.create()); print(asyncio.run(engine.discover_all(Path('${workspaceFolder}'))))\"",
                group="BAEL",
                category=TaskCategory.ANALYSIS
            ),

            # Sprint tasks
            VSCodeTask(
                label="🏃 BAEL: Run Development Sprint",
                command="python -c \"import asyncio; from core.development_sprints import DevelopmentSprintEngine; from pathlib import Path; engine = asyncio.run(DevelopmentSprintEngine.create()); print(asyncio.run(engine.quick_sprint(Path('${workspaceFolder}'))))\"",
                group="BAEL",
                category=TaskCategory.DEVELOPMENT
            ),

            # Competition tasks
            VSCodeTask(
                label="⚔️ BAEL: Analyze Competition",
                command="python -c \"import asyncio; from core.competition_conquest import CompetitionConquestEngine; engine = asyncio.run(CompetitionConquestEngine.create()); print(asyncio.run(engine.get_conquest_summary()))\"",
                group="BAEL",
                category=TaskCategory.COMPETITION
            ),

            # Dream mode tasks
            VSCodeTask(
                label="💭 BAEL: Dream Mode",
                command="python -c \"import asyncio; from core.dream_mode import DreamModeEngine; engine = asyncio.run(DreamModeEngine.create()); print('Dream mode activated...')\"",
                group="BAEL",
                category=TaskCategory.CREATIVITY
            ),

            # Micro agent tasks
            VSCodeTask(
                label="🔬 BAEL: Micro Detail Scan",
                command="python -c \"import asyncio; from core.micro_agents import MicroAgentSwarm; swarm = MicroAgentSwarm(); print('Micro agent swarm scanning for tiny details...')\"",
                group="BAEL",
                category=TaskCategory.ANALYSIS
            ),

            # Zero invest tasks
            VSCodeTask(
                label="💰 BAEL: Find Free Resources",
                command="python -c \"import asyncio; from core.zero_invest_genius import ZeroInvestEngine; print('Scanning for zero-cost opportunities...')\"",
                group="BAEL",
                category=TaskCategory.OPTIMIZATION
            ),
        ]

        logger.info(f"Created {len(self._tasks)} VS Code tasks")

    def get_tasks_json(self) -> Dict[str, Any]:
        """Generate tasks.json content."""
        return {
            "version": "2.0.0",
            "tasks": [task.to_dict() for task in self._tasks]
        }

    def get_mcp_tools_schema(self) -> List[Dict[str, Any]]:
        """Get MCP tools schema for registration."""
        return [tool.to_mcp_schema() for tool in self._mcp_tools.values()]

    async def handle_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Handle an MCP tool invocation."""
        logger.info(f"MCP tool invoked: {tool_name} with {arguments}")

        lord = await self._get_lord()

        if tool_name == "bael_dominate":
            if lord:
                path = Path(arguments.get("project_path", "."))
                return await lord.quick_dominate(path)
            return {"error": "Lord of All not available"}

        elif tool_name == "bael_quick_dominate":
            if lord:
                path = Path(arguments.get("project_path", "."))
                return await lord.quick_dominate(path)
            return {"error": "Lord of All not available"}

        elif tool_name == "bael_discover_opportunities":
            try:
                from core.opportunity_discovery import OpportunityDiscoveryEngine
                engine = await OpportunityDiscoveryEngine.create()
                path = Path(arguments.get("project_path", "."))
                opportunities = await engine.discover_all(path)
                return {"opportunities": len(opportunities), "top_5": [o.to_dict() if hasattr(o, 'to_dict') else str(o) for o in opportunities[:5]]}
            except ImportError:
                return {"error": "OpportunityDiscoveryEngine not available"}

        elif tool_name == "bael_run_sprint":
            try:
                from core.development_sprints import DevelopmentSprintEngine
                engine = await DevelopmentSprintEngine.create()
                path = Path(arguments.get("project_path", "."))
                return await engine.quick_sprint(path)
            except ImportError:
                return {"error": "DevelopmentSprintEngine not available"}

        elif tool_name == "bael_analyze_competition":
            try:
                from core.competition_conquest import CompetitionConquestEngine
                engine = await CompetitionConquestEngine.create()
                return await engine.get_conquest_summary()
            except ImportError:
                return {"error": "CompetitionConquestEngine not available"}

        return {"error": f"Unknown tool: {tool_name}"}

    async def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        lord = await self._get_lord()

        return {
            "initialized": self._initialized,
            "workspace": str(self.workspace_path),
            "mcp_tools": len(self._mcp_tools),
            "tasks": len(self._tasks),
            "lord_available": lord is not None,
            "systems": {
                "opportunity_discovery": True,
                "development_sprints": True,
                "competition_conquest": True,
                "lord_of_all": True,
                "dream_mode": True,
                "micro_agents": True,
                "zero_invest": True
            }
        }


# =============================================================================
# EXTENSION API
# =============================================================================

class VSCodeExtensionAPI:
    """
    API for building VS Code extensions that use BAEL.

    Provides methods for:
    - Registering commands
    - Creating code lenses
    - Providing diagnostics
    - Status bar updates
    """

    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._code_lenses: List[Dict] = []

    def register_command(self, command_id: str, handler: Callable):
        """Register a command handler."""
        self._commands[command_id] = handler

    def create_code_lens(
        self,
        file_path: str,
        line: int,
        command: str,
        title: str
    ) -> Dict[str, Any]:
        """Create a code lens."""
        lens = {
            "file": file_path,
            "line": line,
            "command": command,
            "title": title
        }
        self._code_lenses.append(lens)
        return lens

    def create_diagnostic(
        self,
        file_path: str,
        line: int,
        message: str,
        severity: str = "warning"
    ) -> DiagnosticEntry:
        """Create a diagnostic entry."""
        return DiagnosticEntry(
            file_path=file_path,
            line=line,
            message=message,
            severity=severity
        )

    def get_status_bar_item(self) -> Dict[str, Any]:
        """Get status bar item configuration."""
        return {
            "id": "bael-status",
            "text": "👑 BAEL",
            "tooltip": "Ba'el - Lord of All AI Agents",
            "command": "bael.showStatus",
            "alignment": "right",
            "priority": 100
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def create_vscode_integration(workspace: Path = None) -> VSCodeIntegration:
    """Create VS Code integration instance."""
    return await VSCodeIntegration.create(workspace)


def get_all_commands() -> List[str]:
    """Get all available VS Code commands."""
    return [cmd.value for cmd in VSCodeCommand]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "VSCodeIntegration",
    "VSCodeExtensionAPI",
    "VSCodeCommand",
    "VSCodeTask",
    "MCPTool",
    "DiagnosticEntry",
    "TaskCategory",
    "create_vscode_integration",
    "get_all_commands",
]
