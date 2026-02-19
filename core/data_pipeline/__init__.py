"""
BAEL Data Pipeline Engine
=========================

Advanced data processing pipelines with transformations,
validations, and streaming support.

"Data flows through Ba'el like rivers of wisdom." — Ba'el
"""

from .data_pipeline import (
    # Enums
    PipelineStatus,
    StageStatus,
    DataFormat,
    TransformType,
    ValidationLevel,

    # Data structures
    DataRecord,
    Stage,
    Pipeline,
    PipelineResult,
    StageResult,
    PipelineConfig,

    # Classes
    DataPipelineEngine,
    Transform,
    Validator,
    DataSource,
    DataSink,
    StreamProcessor,

    # Instance
    pipeline_engine
)

__all__ = [
    # Enums
    "PipelineStatus",
    "StageStatus",
    "DataFormat",
    "TransformType",
    "ValidationLevel",

    # Data structures
    "DataRecord",
    "Stage",
    "Pipeline",
    "PipelineResult",
    "StageResult",
    "PipelineConfig",

    # Classes
    "DataPipelineEngine",
    "Transform",
    "Validator",
    "DataSource",
    "DataSink",
    "StreamProcessor",

    # Instance
    "pipeline_engine"
]
