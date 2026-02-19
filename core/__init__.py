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
        "maximum_potential": False,
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

    # ═══ Enhanced Subsystems (23 modules) ═══
    enhanced_modules = {
        "omega_mind": "core.omega_mind",
        "genius_amplifier": "core.genius_synthesis",
        "zero_limit": "core.zero_limit_intelligence",
        "consciousness": "core.quantum_consciousness",
        "knowledge_engine": "core.knowledge_synthesis",
        "sacred_math": "core.sacred_mathematics",
        "power_amplifier": "core.power_core",
        "cosmic_optimizer": "core.cosmic_optimization",
        "infinity_engine": "core.infinity_engine",
        "potential_maximizer": "core.infinite_potential",
        "domination": "core.domination",
        "warfare": "core.strategic_warfare",
        "asset_dominator": "core.asset_domination",
        "mastery": "core.absolute_mastery",
        "meta_commander": "core.meta_orchestration",
        "ultimate_controller": "core.ultimate_control",
        "swarm_intelligence": "core.swarm_intelligence",
        "neural_nexus": "core.neural_nexus",
        "transcendence": "core.transcendence",
        "apex_protocol": "core.apex_protocol",
        "temporal_engine": "core.temporal_mastery",
        "dimension_weaver": "core.dimension_weaver",
        "supreme_integration": "core.supreme_integration",
    }

    for mod_name, mod_path in enhanced_modules.items():
        modules[mod_name] = False
        try:
            __import__(mod_path)
            modules[mod_name] = True
        except ImportError:
            pass

    # Check Enhanced Brain
    modules["enhanced_brain"] = False
    try:
        from core.brain.enhanced_brain import EnhancedBaelBrain

        modules["enhanced_brain"] = True
    except ImportError:
        pass

    enhanced_keys = list(enhanced_modules.keys()) + ["enhanced_brain"]

    return {
        "version": __version__,
        "modules": modules,
        "available_count": sum(1 for v in modules.values() if v),
        "total_count": len(modules),
        "core_available": sum(
            1
            for k, v in modules.items()
            if v
            and k
            in [
                "reasoning",
                "memory",
                "llm",
                "personas",
                "tools",
                "rag",
                "swarm",
                "planning",
                "brain",
                "ultimate",
            ]
        ),
        "max_potential_available": sum(
            1
            for k, v in modules.items()
            if v
            and k
            in [
                "thinking",
                "computer_use",
                "proactive",
                "vision",
                "voice",
                "evolution",
                "feedback",
                "dynamic_tools",
                "semantic_cache",
                "hierarchical_memory",
                "maximum_potential",
            ]
        ),
        "enhanced_available": sum(
            1 for k, v in modules.items() if v and k in enhanced_keys
        ),
    }


def get_maximum_potential():
    """Get the Maximum Potential Engine for cutting-edge AI capabilities."""
    try:
        from core.maximum_potential import get_max_potential_engine

        return get_max_potential_engine()
    except ImportError:
        return None


def get_enhanced_brain():
    """Get the Enhanced Brain — unified access to all 23+ subsystems."""
    try:
        from core.brain.enhanced_brain import get_enhanced_brain as _get

        return _get()
    except ImportError:
        return None


__all__ = [
    "get_core_info",
    "get_maximum_potential",
    "get_enhanced_brain",
    "__version__",
]
