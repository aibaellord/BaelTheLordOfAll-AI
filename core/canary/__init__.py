"""
BAEL Canary Release Engine
==========================

Gradual rollout with monitoring.

"Ba'el tests in production, safely." — Ba'el
"""

from .canary_engine import (
    CanaryState,
    CanaryMetric,
    CanaryRelease,
    CanaryConfig,
    CanaryManager,
    canary_manager,
    start_canary,
    promote_canary,
    rollback_canary
)

__all__ = [
    'CanaryState',
    'CanaryMetric',
    'CanaryRelease',
    'CanaryConfig',
    'CanaryManager',
    'canary_manager',
    'start_canary',
    'promote_canary',
    'rollback_canary'
]
