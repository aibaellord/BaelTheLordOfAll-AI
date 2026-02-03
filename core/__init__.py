"""
BAEL - Complete Package Init
Ensures all core modules are properly importable.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BAEL.Core")

# Version info
__version__ = "2.0.0"
__author__ = "BAEL"


def get_core_info() -> Dict[str, Any]:
    """Get information about core modules."""
    modules = {
        # Original core modules
        "reasoning": False,
        "memory": False,
        "llm": False,
        "personas": False,
        "tools": False,
        "rag": False,
        "swarm": False,
        "planning": False,
        "brain": False,
        "ultimate": False,
        # Maximum Potential modules (NEW)
        "thinking": False,
        "computer_use": False,
        "proactive": False,
        "vision": False,
        "voice": False,
        "evolution": False,
        "feedback": False,
        "dynamic_tools": False,
        "semantic_cache": False,
        "hierarchical_memory": False,
        "maximum_potential": False
    }

    # Check original modules
    try:
        from core import reasoning
        modules["reasoning"] = True
    except ImportError:
        pass

    try:
        from core import llm
        modules["llm"] = True
    except ImportError:
        pass

    try:
        from core import personas
        modules["personas"] = True
    except ImportError:
        pass

    try:
        from core import tools
        modules["tools"] = True
    except ImportError:
        pass

    try:
        from core import rag
        modules["rag"] = True
    except ImportError:
        pass

    try:
        from core import swarm
        modules["swarm"] = True
    except ImportError:
        pass

    try:
        from core import planning
        modules["planning"] = True
    except ImportError:
        pass

    try:
        from core import brain
        modules["brain"] = True
    except ImportError:
        pass

    try:
        from core import ultimate
        modules["ultimate"] = True
    except ImportError:
        pass

    try:
        from memory import UnifiedMemory
        modules["memory"] = True
    except ImportError:
        pass

    # Check Maximum Potential modules
    try:
        from core import thinking
        modules["thinking"] = True
    except ImportError:
        pass

    try:
        from core import computer_use
        modules["computer_use"] = True
    except ImportError:
        pass

    try:
        from core import proactive
        modules["proactive"] = True
    except ImportError:
        pass

    try:
        from core import vision
        modules["vision"] = True
    except ImportError:
        pass

    try:
        from core import voice
        modules["voice"] = True
    except ImportError:
        pass

    try:
        from core import evolution
        modules["evolution"] = True
    except ImportError:
        pass

    try:
        from core import feedback
        modules["feedback"] = True
    except ImportError:
        pass

    try:
        from core.tools import dynamic
        modules["dynamic_tools"] = True
    except ImportError:
        pass

    try:
        from core.cache import semantic
        modules["semantic_cache"] = True
    except ImportError:
        pass

    try:
        from core.context.hierarchical_memory import HierarchicalMemory
        modules["hierarchical_memory"] = True
    except ImportError:
        pass

    try:
        from core.maximum_potential import MaximumPotentialEngine
        modules["maximum_potential"] = True
    except ImportError:
        pass

    return {
        "version": __version__,
        "modules": modules,
        "available_count": sum(1 for v in modules.values() if v),
        "total_count": len(modules),
        "core_available": sum(1 for k, v in modules.items() if v and k in [
            "reasoning", "memory", "llm", "personas", "tools", "rag",
            "swarm", "planning", "brain", "ultimate"
        ]),
        "max_potential_available": sum(1 for k, v in modules.items() if v and k in [
            "thinking", "computer_use", "proactive", "vision", "voice",
            "evolution", "feedback", "dynamic_tools", "semantic_cache",
            "hierarchical_memory", "maximum_potential"
        ])
    }


def get_maximum_potential():
    """Get the Maximum Potential Engine for cutting-edge AI capabilities."""
    try:
        from core.maximum_potential import get_max_potential_engine
        return get_max_potential_engine()
    except ImportError:
        return None


__all__ = ["get_core_info", "get_maximum_potential", "__version__"]
