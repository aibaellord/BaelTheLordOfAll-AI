"""
BAEL Workflow Engine
====================

Self-evolving, self-healing workflow automation that surpasses n8n.

Features:
- Visual DAG workflow builder
- Self-healing on failures
- Auto-optimization
- Genetic workflow evolution
- Real-time monitoring
"""

from .workflow_orchestrator import (
    # Enums
    NodeType,
    NodeStatus,
    WorkflowStatus,
    TriggerType,
    RetryStrategy,
    ExecutionMode,

    # Dataclasses
    NodeConfig,
    WorkflowNode,
    WorkflowEdge,
    WorkflowDefinition,
    ExecutionContext,
    NodeResult,
    WorkflowResult,

    # Main classes
    WorkflowOrchestrator,
    WorkflowRegistry,
    WorkflowScheduler,
    WorkflowMonitor,

    # Instance
    workflow_engine
)

__all__ = [
    # Enums
    "NodeType",
    "NodeStatus",
    "WorkflowStatus",
    "TriggerType",
    "RetryStrategy",
    "ExecutionMode",

    # Dataclasses
    "NodeConfig",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowDefinition",
    "ExecutionContext",
    "NodeResult",
    "WorkflowResult",

    # Classes
    "WorkflowOrchestrator",
    "WorkflowRegistry",
    "WorkflowScheduler",
    "WorkflowMonitor",

    # Instance
    "workflow_engine"
]
