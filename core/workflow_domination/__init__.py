# BAEL - Workflow Domination Engine
# "Surpassing n8n by Leagues"

"""
Workflow Domination Engine - Self-improving automated workflows.

This module provides workflow automation that surpasses n8n:
- Self-healing workflows that auto-repair on failure
- Self-optimizing with learning from execution
- Genetic evolution of workflow DNA
- Reality branching to explore alternatives
- Dream generation for novel workflows
- Predictive execution for pre-running likely paths
- Agent orchestration for specialized tasks
- Sacred geometry optimization

Usage:
    from core.workflow_domination import WorkflowDominationEngine

    engine = WorkflowDominationEngine()
    workflow = await engine.generate_from_description(
        "Every morning at 8am, check GitHub for new issues..."
    )
    best = await engine.evolve(workflows, generations=100)
"""

from .workflow_domination_engine import (
    WorkflowDominationEngine,
    WorkflowDNA,
    WorkflowGene,
    Mutation,
    WorkflowConfig,
    WorkflowResult,
)

__all__ = [
    "WorkflowDominationEngine",
    "WorkflowDNA",
    "WorkflowGene",
    "Mutation",
    "WorkflowConfig",
    "WorkflowResult",
]
