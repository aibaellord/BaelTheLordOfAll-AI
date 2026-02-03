"""
BAEL - Dynamic Tool System
Dynamic tool creation, composition, and learning.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Tools.Dynamic")


class ToolType(Enum):
    """Types of dynamic tools."""
    GENERATED = "generated"
    COMPOSED = "composed"
    LEARNED = "learned"
    WRAPPED = "wrapped"
    PIPELINE = "pipeline"


class ToolCategory(Enum):
    """Tool categories."""
    CODE = "code"
    FILE = "file"
    WEB = "web"
    DATA = "data"
    SYSTEM = "system"
    AI = "ai"
    CUSTOM = "custom"


@dataclass
class ToolSignature:
    """Tool function signature."""
    name: str
    parameters: Dict[str, Dict[str, Any]]
    return_type: str
    description: str


@dataclass
class DynamicTool:
    """A dynamically created tool."""
    id: str
    name: str
    description: str
    tool_type: ToolType
    category: ToolCategory
    signature: ToolSignature
    handler: Optional[Callable] = None
    code: Optional[str] = None
    version: str = "1.0.0"
    usage_count: int = 0
    success_rate: float = 1.0


@dataclass
class ToolComposition:
    """Composition of multiple tools."""
    id: str
    name: str
    description: str
    tools: List[str]
    flow: List[Dict[str, Any]]


# Lazy imports
def get_tool_factory():
    """Get the tool factory."""
    from .tool_factory import DynamicToolFactory
    return DynamicToolFactory()


def get_tool_composer():
    """Get the tool composer."""
    from .tool_composer import ToolComposer
    return ToolComposer()


def get_tool_learner():
    """Get the tool learner."""
    from .tool_learner import ToolLearner
    return ToolLearner()


__all__ = [
    "ToolType",
    "ToolCategory",
    "ToolSignature",
    "DynamicTool",
    "ToolComposition",
    "get_tool_factory",
    "get_tool_composer",
    "get_tool_learner"
]
