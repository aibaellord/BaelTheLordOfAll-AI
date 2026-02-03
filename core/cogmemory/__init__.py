"""
BAEL - Cognitive Memory System
Advanced memory management for cognitive processing.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.CogMemory")

# Re-export from main memory module
try:
    from memory import UnifiedMemory
    __all__ = ["UnifiedMemory"]
except ImportError:
    __all__ = []
    logger.warning("Cognitive memory module not fully loaded")
