"""
BAEL Saga Engine
================

Saga pattern for distributed transactions with compensation.

"Ba'el orchestrates sagas across the multiverse." — Ba'el
"""

from .saga_engine import (
    # Enums
    SagaState,
    StepState,
    CompensationStrategy,

    # Data structures
    SagaStep,
    SagaDefinition,
    SagaExecution,

    # Engine
    SagaOrchestrator,

    # Convenience
    saga_orchestrator,
)

__all__ = [
    'SagaState',
    'StepState',
    'CompensationStrategy',
    'SagaStep',
    'SagaDefinition',
    'SagaExecution',
    'SagaOrchestrator',
    'saga_orchestrator',
]
