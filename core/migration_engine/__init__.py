"""
BAEL Migration Engine
=====================

Database migration and schema management with:
- Version tracking
- Up/down migrations
- Schema diffing
- Rollback support
- Migration generation

"Ba'el evolves the foundations of reality." — Ba'el
"""

from .migration_engine import (
    # Enums
    MigrationStatus,
    MigrationDirection,
    SchemaChangeType,

    # Data structures
    Migration,
    MigrationHistory,
    SchemaChange,
    MigrationPlan,
    MigrationConfig,

    # Classes
    MigrationEngine,
    MigrationRunner,
    SchemaManager,
    MigrationGenerator,

    # Instance
    migration_engine
)

__all__ = [
    'MigrationStatus',
    'MigrationDirection',
    'SchemaChangeType',
    'Migration',
    'MigrationHistory',
    'SchemaChange',
    'MigrationPlan',
    'MigrationConfig',
    'MigrationEngine',
    'MigrationRunner',
    'SchemaManager',
    'MigrationGenerator',
    'migration_engine'
]
