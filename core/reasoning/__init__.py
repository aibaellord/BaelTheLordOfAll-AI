"""
BAEL Reasoning & Reflection Engine
====================================

Advanced reasoning and meta-cognitive capabilities.
Enables chain-of-thought, self-critique, and reflection.

Components:
- ChainOfThought: Step-by-step reasoning
- SelfCritique: Self-evaluation and correction
- MetaCognition: Thinking about thinking
- ReasoningTree: Branching logical exploration
- ReflectionLoop: Iterative improvement
- CausalReasoning: Cause-effect analysis
"""

from .causal_reasoning import (CausalGraph, CausalReasoningEngine, CausalRelation)
from .chain_of_thought import (ChainOfThought, ReasoningChain, ThoughtStep,
                               ThoughtType)
from .meta_cognition import (CognitiveState, ConfidenceAssessment,
                             MetaCognition, UncertaintyModel)
from .reasoning_tree import (BranchStrategy, ExplorationResult, ReasoningTree,
                             TreeNode)
from .reflection_loop import (AdaptationStrategy, LearningOutcome,
                              ReflectionCycle, ReflectionLoop)
from .self_critique import (Critique, CritiqueType, ImprovementSuggestion,
                            SelfCritique)

__all__ = [
    # Chain of Thought
    "ChainOfThought",
    "ThoughtStep",
    "ReasoningChain",
    "ThoughtType",
    # Self Critique
    "SelfCritique",
    "Critique",
    "CritiqueType",
    "ImprovementSuggestion",
    # Meta Cognition
    "MetaCognition",
    "CognitiveState",
    "ConfidenceAssessment",
    "UncertaintyModel",
    # Reasoning Tree
    "ReasoningTree",
    "TreeNode",
    "BranchStrategy",
    "ExplorationResult",
    # Reflection Loop
    "ReflectionLoop",
    "ReflectionCycle",
    "LearningOutcome",
    "AdaptationStrategy",
    # Causal Reasoning
    "CausalReasoningEngine",
    "CausalGraph",
    "CausalRelation",
]
