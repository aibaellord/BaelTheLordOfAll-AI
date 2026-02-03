"""
BAEL Package Initialization
The Lord of All AI Agents
"""

__version__ = "1.0.0"
__author__ = "BAEL Development Team"
__description__ = "The Ultimate AI Agent Orchestration System"

# Core exports
from pathlib import Path

BAEL_ROOT = Path(__file__).parent
CONFIG_DIR = BAEL_ROOT / "config"
DATA_DIR = BAEL_ROOT / "data"

def get_version() -> str:
    """Get BAEL version."""
    return __version__
