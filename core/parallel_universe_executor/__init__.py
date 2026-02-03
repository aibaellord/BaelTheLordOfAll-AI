"""
BAEL - Parallel Universe Executor Module
Execute multiple solution paths simultaneously.
"""

from .multiverse_engine import (
    ParallelUniverseExecutor,
    ExecutionPath,
    MultiverseResult,
    UniverseState,
    ExecutionStrategy,
    PathState,
    SelectionCriteria,
    get_parallel_executor
)

__all__ = [
    "ParallelUniverseExecutor",
    "ExecutionPath",
    "MultiverseResult",
    "UniverseState",
    "ExecutionStrategy",
    "PathState",
    "SelectionCriteria",
    "get_parallel_executor"
]
