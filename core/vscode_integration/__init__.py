"""
BAEL - VS Code Integration
SEAMLESS IDE INTEGRATION FOR TOTAL DOMINANCE

This module provides:
- VS Code MCP tools for all BAEL capabilities
- Task definitions for VS Code
- Extension API for VS Code extensions
- Real-time integration with editor
"""

from .vscode_integration import (
    VSCodeIntegration,
    VSCodeExtensionAPI,
    VSCodeCommand,
    VSCodeTask,
    MCPTool,
    DiagnosticEntry,
    TaskCategory,
    create_vscode_integration,
    get_all_commands,
)

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
