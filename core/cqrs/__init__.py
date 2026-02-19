"""
BAEL CQRS Engine
================

Command Query Responsibility Segregation pattern.

"Ba'el separates command from query for supreme efficiency." — Ba'el
"""

from .cqrs_engine import (
    # Enums
    CommandStatus,
    QueryType,

    # Data structures
    Command,
    CommandResult,
    Query,
    QueryResult,

    # Handlers
    CommandHandler,
    QueryHandler,

    # Engine
    CommandBus,
    QueryBus,
    CQRSEngine,

    # Convenience
    command_bus,
    query_bus,
    cqrs_engine,
)

__all__ = [
    'CommandStatus',
    'QueryType',
    'Command',
    'CommandResult',
    'Query',
    'QueryResult',
    'CommandHandler',
    'QueryHandler',
    'CommandBus',
    'QueryBus',
    'CQRSEngine',
    'command_bus',
    'query_bus',
    'cqrs_engine',
]
