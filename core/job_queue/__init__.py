"""
BAEL Job Queue Engine
======================

Background job processing with workers and priorities.

"Ba'el orchestrates all tasks in perfect order." — Ba'el
"""

from .job_queue_engine import (
    # Enums
    JobStatus,
    JobPriority,
    JobType,
    RetryStrategy,

    # Data structures
    JobResult,
    Job,
    Worker,
    JobQueueConfig,

    # Engine
    JobQueueEngine,

    # Decorators
    job,

    # Instance
    job_queue_engine,
)

__all__ = [
    # Enums
    "JobStatus",
    "JobPriority",
    "JobType",
    "RetryStrategy",

    # Data structures
    "JobResult",
    "Job",
    "Worker",
    "JobQueueConfig",

    # Engine
    "JobQueueEngine",

    # Decorators
    "job",

    # Instance
    "job_queue_engine",
]
