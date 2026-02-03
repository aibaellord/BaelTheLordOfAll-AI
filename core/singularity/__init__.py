"""
BAEL Singularity - The Ultimate Unified Intelligence Layer

The Singularity is the apex of BAEL's architecture.
It unifies ALL 200+ capabilities into a single, omnipotent interface.

Components:
- Singularity: Main unified interface
- IntegrationEngine: Connects capabilities into workflows
- DecisionPipeline: 10-stage decision making process
- CapabilityRegistry: Dynamic capability loading

Usage:
    from core.singularity import awaken, SingularityMode

    singularity = await awaken(SingularityMode.TRANSCENDENT)
    result = await singularity.think("What is consciousness?")
    result = await singularity.decide("Should we proceed?")
    result = await singularity.maximum_potential("Build AGI")
"""

from .decision_pipeline import (DecisionContext, DecisionPipeline,
                                DecisionResult, PipelineStage, StageResult,
                                create_decision_pipeline)
from .integration_engine import (IntegrationConfig, IntegrationEngine,
                                 IntegrationPattern, IntegrationResult,
                                 SingularityIntegrations, WorkflowBuilder,
                                 create_integration_engine,
                                 create_workflow_builder)
from .singularity import (CapabilityDomain, CapabilityRegistry,
                          CapabilityStatus, Singularity, SingularityConfig,
                          SingularityMode, SingularityState, awaken,
                          get_singularity)

__all__ = [
    # Core Singularity
    "Singularity",
    "SingularityMode",
    "SingularityConfig",
    "SingularityState",
    "CapabilityDomain",
    "CapabilityRegistry",
    "CapabilityStatus",
    "awaken",
    "get_singularity",

    # Integration Engine
    "IntegrationEngine",
    "IntegrationPattern",
    "IntegrationConfig",
    "IntegrationResult",
    "SingularityIntegrations",
    "WorkflowBuilder",
    "create_integration_engine",
    "create_workflow_builder",

    # Decision Pipeline
    "DecisionPipeline",
    "PipelineStage",
    "StageResult",
    "DecisionContext",
    "DecisionResult",
    "create_decision_pipeline",
]
