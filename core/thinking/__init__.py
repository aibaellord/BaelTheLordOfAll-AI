"""
BAEL - Advanced Thinking System
Cutting-edge reasoning capabilities including extended thinking,
tree-of-thought, graph-of-thought, and self-consistency.

This module provides o1/Claude-style deep reasoning that surpasses
standard chain-of-thought approaches.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Thinking")


class ThinkingMode(Enum):
    """Available thinking modes."""
    QUICK = "quick"           # Fast, single-pass
    STANDARD = "standard"     # Normal CoT
    EXTENDED = "extended"     # Deep multi-step reasoning
    TREE = "tree"            # Tree-of-thought branching
    GRAPH = "graph"          # Non-linear graph reasoning
    CONSENSUS = "consensus"  # Multi-sample voting


class ThinkingDepth(Enum):
    """Depth of thinking process."""
    SHALLOW = 1    # 1-2 reasoning steps
    MODERATE = 2   # 3-5 reasoning steps
    DEEP = 3       # 6-10 reasoning steps
    EXHAUSTIVE = 4 # 10+ reasoning steps


@dataclass
class ThinkingStep:
    """A single step in the thinking process."""
    id: str
    content: str
    step_type: str  # "observation", "hypothesis", "analysis", "conclusion"
    confidence: float = 0.0
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThinkingTrace:
    """Complete trace of a thinking process."""
    query: str
    mode: ThinkingMode
    steps: List[ThinkingStep] = field(default_factory=list)
    branches: Dict[str, List[str]] = field(default_factory=dict)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    total_tokens: int = 0
    thinking_time_ms: float = 0.0


@dataclass
class ThinkingConfig:
    """Configuration for thinking process."""
    mode: ThinkingMode = ThinkingMode.EXTENDED
    depth: ThinkingDepth = ThinkingDepth.DEEP
    max_steps: int = 20
    branch_factor: int = 3  # For tree/graph modes
    consensus_samples: int = 5  # For consensus mode
    show_thinking: bool = True
    temperature: float = 0.7
    reflection_enabled: bool = True


# Lazy imports for main components
def get_extended_thinker():
    """Get the extended thinking engine."""
    from .extended_thinking import ExtendedThinker
    return ExtendedThinker()


def get_tree_thinker():
    """Get the tree-of-thought engine."""
    from .tree_of_thought import TreeOfThought
    return TreeOfThought()


def get_graph_thinker():
    """Get the graph-of-thought engine."""
    from .graph_of_thought import GraphOfThought
    return GraphOfThought()


def get_consensus_engine():
    """Get the self-consistency engine."""
    from .self_consistency import SelfConsistency
    return SelfConsistency()


__all__ = [
    "ThinkingMode",
    "ThinkingDepth",
    "ThinkingStep",
    "ThinkingTrace",
    "ThinkingConfig",
    "get_extended_thinker",
    "get_tree_thinker",
    "get_graph_thinker",
    "get_consensus_engine"
]
