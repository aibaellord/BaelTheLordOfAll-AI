"""
BAEL - Model Context Protocol (MCP) Server
Exposes BAEL capabilities through the MCP protocol for Claude Desktop integration.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.MCP")

# Export main server class when available
try:
    from .server import MCPServer, start_server
    __all__ = ["MCPServer", "start_server"]
except ImportError:
    __all__ = []
    logger.warning("MCP server module not fully loaded")


def get_mcp_info() -> Dict[str, Any]:
    """Get MCP server information."""
    return {
        "name": "BAEL MCP Server",
        "version": "1.0.0",
        "protocol": "MCP 1.0",
        "description": "Model Context Protocol server for BAEL AI capabilities",
        "capabilities": {
            "tools": True,
            "prompts": True,
            "resources": True,
            "sampling": False
        },
        "tools": [
            "bael_think",
            "bael_research",
            "bael_analyze_code",
            "bael_execute_code",
            "bael_memory_search",
            "bael_spawn_agent",
            "bael_run_workflow"
        ],
        "prompts": [
            "bael_architect",
            "bael_code_review",
            "bael_explain"
        ]
    }
