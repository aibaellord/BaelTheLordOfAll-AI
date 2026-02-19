"""
BAEL Data Pipeline Engine
=========================

Comprehensive data processing framework with:
- ETL (Extract, Transform, Load) pipelines
- Stream processing
- Data validation
- Multiple data formats
- Parallel execution
- Error handling and recovery

"Ba'el transforms chaos into order, data into wisdom." — Ba'el
"""

import asyncio
import logging
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Awaitable, Union, AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import uuid
import traceback
from pathlib import Path
import hashlib
import re

logger = logging.getLogger("BAEL.DataPipeline")


# ============================================================================
# ENUMS
# ============================================================================

class PipelineStatus(Enum):
    """Status of a pipeline."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataFormat(Enum):
    """Supported data formats."""
    JSON = "json"
    CSV = "csv"
    TEXT = "text"
    BINARY = "binary"
    DICT = "dict"
    LIST = "list"
    PARQUET = "parquet"
    XML = "xml"
    YAML = "yaml"


class TransformType(Enum):
    """Types of data transformations."""
    MAP = "map"             # Apply function to each record
    FILTER = "filter"       # Filter records
    REDUCE = "reduce"       # Aggregate records
    FLATMAP = "flatmap"     # Map and flatten
    GROUP = "group"         # Group by key
    SORT = "sort"           # Sort records
    DEDUPE = "dedupe"       # Remove duplicates
    SAMPLE = "sample"       # Sample records
    LIMIT = "limit"         # Limit record count
    JOIN = "join"           # Join with another source
    SPLIT = "split"         # Split into multiple streams
    MERGE = "merge"         # Merge multiple streams
    WINDOW = "window"       # Windowing for streams


class ValidationLevel(Enum):
    """Validation strictness levels."""
    NONE = "none"           # No validation
    WARN = "warn"           # Log warnings
    STRICT = "strict"       # Fail on invalid
    QUARANTINE = "quarantine"  # Move invalid to quarantine


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DataRecord:
    """A single data record in the pipeline."""
    data: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'errors': self.errors
        }

    def clone(self, data: Any = None) -> 'DataRecord':
        """Create a copy with optional new data."""
        return DataRecord(
            data=data if data is not None else self.data,
            id=str(uuid.uuid4()),
            source=self.source,
            timestamp=datetime.now(),
            metadata=self.metadata.copy(),
            errors=self.errors.copy()
        )


@dataclass
class StageResult:
    """Result of a stage execution."""
    stage_id: str
    status: StageStatus
    input_count: int
    output_count: int
    error_count: int
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Stage:
    """A single stage in a pipeline."""
    id: str
    name: str
    transform_type: TransformType
    transform: Callable

    # Configuration
    parallel: bool = False
    max_workers: int = 4
    batch_size: int = 100
    timeout_seconds: float = 300.0
    retry_count: int = 0
    retry_delay_seconds: float = 1.0

    # Validation
    validation_level: ValidationLevel = ValidationLevel.NONE
    validator: Optional[Callable[[DataRecord], bool]] = None

    # State
    status: StageStatus = StageStatus.PENDING
    result: Optional[StageResult] = None

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Pipeline:
    """A data processing pipeline."""
    id: str
    name: str
    stages: List[Stage]

    # Configuration
    continue_on_error: bool = False
    max_records: Optional[int] = None
    enable_checkpoints: bool = False
    checkpoint_interval: int = 1000

    # State
    status: PipelineStatus = PipelineStatus.CREATED
    current_stage_index: int = 0
    processed_records: int = 0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    pipeline_id: str
    status: PipelineStatus
    stages: List[StageResult]
    total_input: int
    total_output: int
    total_errors: int
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    checkpoints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline engine."""
    max_concurrent_pipelines: int = 5
    default_batch_size: int = 100
    default_timeout_seconds: float = 300.0
    enable_monitoring: bool = True
    checkpoint_directory: str = "./checkpoints"


# ============================================================================
# TRANSFORM CLASS
# ============================================================================

class Transform:
    """
    Collection of common data transformations.
    """

    @staticmethod
    def map(func: Callable[[Any], Any]) -> Callable[[DataRecord], DataRecord]:
        """Create a map transformation."""
        def transform(record: DataRecord) -> DataRecord:
            return record.clone(data=func(record.data))
        return transform

    @staticmethod
    def filter(predicate: Callable[[Any], bool]) -> Callable[[DataRecord], Optional[DataRecord]]:
        """Create a filter transformation."""
        def transform(record: DataRecord) -> Optional[DataRecord]:
            if predicate(record.data):
                return record
            return None
        return transform

    @staticmethod
    def field_map(field: str, func: Callable[[Any], Any]) -> Callable[[DataRecord], DataRecord]:
        """Map a specific field in dict data."""
        def transform(record: DataRecord) -> DataRecord:
            data = record.data.copy() if isinstance(record.data, dict) else record.data
            if isinstance(data, dict) and field in data:
                data[field] = func(data[field])
            return record.clone(data=data)
        return transform

    @staticmethod
    def rename_field(old_name: str, new_name: str) -> Callable[[DataRecord], DataRecord]:
        """Rename a field in dict data."""
        def transform(record: DataRecord) -> DataRecord:
            data = record.data.copy() if isinstance(record.data, dict) else record.data
            if isinstance(data, dict) and old_name in data:
                data[new_name] = data.pop(old_name)
            return record.clone(data=data)
        return transform

    @staticmethod
    def add_field(field: str, value_or_func: Union[Any, Callable[[Any], Any]]) -> Callable[[DataRecord], DataRecord]:
        """Add a field to dict data."""
        def transform(record: DataRecord) -> DataRecord:
            data = record.data.copy() if isinstance(record.data, dict) else {'value': record.data}
            if callable(value_or_func):
                data[field] = value_or_func(record.data)
            else:
                data[field] = value_or_func
            return record.clone(data=data)
        return transform

    @staticmethod
    def remove_fields(*fields: str) -> Callable[[DataRecord], DataRecord]:
        """Remove fields from dict data."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, dict):
                data = {k: v for k, v in record.data.items() if k not in fields}
                return record.clone(data=data)
            return record
        return transform

    @staticmethod
    def select_fields(*fields: str) -> Callable[[DataRecord], DataRecord]:
        """Select only specified fields from dict data."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, dict):
                data = {k: v for k, v in record.data.items() if k in fields}
                return record.clone(data=data)
            return record
        return transform

    @staticmethod
    def flatten() -> Callable[[DataRecord], List[DataRecord]]:
        """Flatten list data into multiple records."""
        def transform(record: DataRecord) -> List[DataRecord]:
            if isinstance(record.data, list):
                return [record.clone(data=item) for item in record.data]
            return [record]
        return transform

    @staticmethod
    def parse_json() -> Callable[[DataRecord], DataRecord]:
        """Parse JSON string data."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, str):
                return record.clone(data=json.loads(record.data))
            return record
        return transform

    @staticmethod
    def to_json() -> Callable[[DataRecord], DataRecord]:
        """Convert data to JSON string."""
        def transform(record: DataRecord) -> DataRecord:
            return record.clone(data=json.dumps(record.data))
        return transform

    @staticmethod
    def lowercase() -> Callable[[DataRecord], DataRecord]:
        """Convert string data to lowercase."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, str):
                return record.clone(data=record.data.lower())
            return record
        return transform

    @staticmethod
    def uppercase() -> Callable[[DataRecord], DataRecord]:
        """Convert string data to uppercase."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, str):
                return record.clone(data=record.data.upper())
            return record
        return transform

    @staticmethod
    def strip() -> Callable[[DataRecord], DataRecord]:
        """Strip whitespace from string data."""
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, str):
                return record.clone(data=record.data.strip())
            return record
        return transform

    @staticmethod
    def regex_extract(pattern: str, group: int = 0) -> Callable[[DataRecord], DataRecord]:
        """Extract data using regex."""
        compiled = re.compile(pattern)
        def transform(record: DataRecord) -> DataRecord:
            if isinstance(record.data, str):
                match = compiled.search(record.data)
                if match:
                    return record.clone(data=match.group(group))
            return record
        return transform

    @staticmethod
    def type_cast(target_type: type) -> Callable[[DataRecord], DataRecord]:
        """Cast data to a specific type."""
        def transform(record: DataRecord) -> DataRecord:
            try:
                return record.clone(data=target_type(record.data))
            except (ValueError, TypeError):
                record.errors.append(f"Failed to cast to {target_type.__name__}")
                return record
        return transform


# ============================================================================
# VALIDATOR CLASS
# ============================================================================

class Validator:
    """
    Collection of common data validators.
    """

    @staticmethod
    def not_null() -> Callable[[DataRecord], bool]:
        """Validate data is not None."""
        def validate(record: DataRecord) -> bool:
            return record.data is not None
        return validate

    @staticmethod
    def not_empty() -> Callable[[DataRecord], bool]:
        """Validate data is not empty."""
        def validate(record: DataRecord) -> bool:
            if record.data is None:
                return False
            if isinstance(record.data, (str, list, dict)):
                return len(record.data) > 0
            return True
        return validate

    @staticmethod
    def is_type(*types: type) -> Callable[[DataRecord], bool]:
        """Validate data is of specific type(s)."""
        def validate(record: DataRecord) -> bool:
            return isinstance(record.data, types)
        return validate

    @staticmethod
    def has_fields(*fields: str) -> Callable[[DataRecord], bool]:
        """Validate dict data has required fields."""
        def validate(record: DataRecord) -> bool:
            if not isinstance(record.data, dict):
                return False
            return all(f in record.data for f in fields)
        return validate

    @staticmethod
    def matches_regex(pattern: str) -> Callable[[DataRecord], bool]:
        """Validate string data matches regex."""
        compiled = re.compile(pattern)
        def validate(record: DataRecord) -> bool:
            if not isinstance(record.data, str):
                return False
            return compiled.match(record.data) is not None
        return validate

    @staticmethod
    def in_range(min_val: Any = None, max_val: Any = None) -> Callable[[DataRecord], bool]:
        """Validate numeric data is in range."""
        def validate(record: DataRecord) -> bool:
            try:
                value = float(record.data)
                if min_val is not None and value < min_val:
                    return False
                if max_val is not None and value > max_val:
                    return False
                return True
            except (ValueError, TypeError):
                return False
        return validate

    @staticmethod
    def length_between(min_len: int = 0, max_len: int = float('inf')) -> Callable[[DataRecord], bool]:
        """Validate data length is in range."""
        def validate(record: DataRecord) -> bool:
            try:
                length = len(record.data)
                return min_len <= length <= max_len
            except TypeError:
                return False
        return validate

    @staticmethod
    def custom(func: Callable[[Any], bool]) -> Callable[[DataRecord], bool]:
        """Custom validation function."""
        def validate(record: DataRecord) -> bool:
            return func(record.data)
        return validate

    @staticmethod
    def all_of(*validators: Callable[[DataRecord], bool]) -> Callable[[DataRecord], bool]:
        """Combine validators with AND logic."""
        def validate(record: DataRecord) -> bool:
            return all(v(record) for v in validators)
        return validate

    @staticmethod
    def any_of(*validators: Callable[[DataRecord], bool]) -> Callable[[DataRecord], bool]:
        """Combine validators with OR logic."""
        def validate(record: DataRecord) -> bool:
            return any(v(record) for v in validators)
        return validate


# ============================================================================
# DATA SOURCE
# ============================================================================

class DataSource:
    """
    Base class for data sources.
    """

    def __init__(self, source_id: str = None):
        """Initialize data source."""
        self.source_id = source_id or str(uuid.uuid4())

    async def read(self) -> AsyncIterator[DataRecord]:
        """Read data records."""
        raise NotImplementedError

    async def read_all(self) -> List[DataRecord]:
        """Read all records at once."""
        records = []
        async for record in self.read():
            records.append(record)
        return records

    @staticmethod
    def from_list(data: List[Any], source: str = "list") -> 'ListDataSource':
        """Create source from a list."""
        return ListDataSource(data, source)

    @staticmethod
    def from_file(path: str, format: DataFormat = DataFormat.JSON) -> 'FileDataSource':
        """Create source from a file."""
        return FileDataSource(path, format)

    @staticmethod
    def from_dict(data: Dict[str, Any], source: str = "dict") -> 'DictDataSource':
        """Create source from a dict."""
        return DictDataSource(data, source)


class ListDataSource(DataSource):
    """Data source from a list."""

    def __init__(self, data: List[Any], source: str = "list"):
        super().__init__()
        self.data = data
        self.source = source

    async def read(self) -> AsyncIterator[DataRecord]:
        for item in self.data:
            yield DataRecord(data=item, source=self.source)


class DictDataSource(DataSource):
    """Data source from a dictionary."""

    def __init__(self, data: Dict[str, Any], source: str = "dict"):
        super().__init__()
        self.data = data
        self.source = source

    async def read(self) -> AsyncIterator[DataRecord]:
        for key, value in self.data.items():
            yield DataRecord(data={'key': key, 'value': value}, source=self.source)


class FileDataSource(DataSource):
    """Data source from a file."""

    def __init__(self, path: str, format: DataFormat = DataFormat.JSON):
        super().__init__()
        self.path = Path(path)
        self.format = format

    async def read(self) -> AsyncIterator[DataRecord]:
        content = self.path.read_text()

        if self.format == DataFormat.JSON:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    yield DataRecord(data=item, source=str(self.path))
            else:
                yield DataRecord(data=data, source=str(self.path))

        elif self.format == DataFormat.CSV:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                yield DataRecord(data=dict(row), source=str(self.path))

        elif self.format == DataFormat.TEXT:
            for line in content.splitlines():
                yield DataRecord(data=line, source=str(self.path))

        else:
            yield DataRecord(data=content, source=str(self.path))


# ============================================================================
# DATA SINK
# ============================================================================

class DataSink:
    """
    Base class for data sinks.
    """

    def __init__(self, sink_id: str = None):
        """Initialize data sink."""
        self.sink_id = sink_id or str(uuid.uuid4())
        self._records: List[DataRecord] = []

    async def write(self, record: DataRecord) -> None:
        """Write a single record."""
        self._records.append(record)

    async def write_batch(self, records: List[DataRecord]) -> None:
        """Write multiple records."""
        for record in records:
            await self.write(record)

    async def flush(self) -> None:
        """Flush any buffered data."""
        pass

    async def close(self) -> None:
        """Close the sink."""
        await self.flush()

    def get_records(self) -> List[DataRecord]:
        """Get collected records."""
        return self._records


class ListDataSink(DataSink):
    """Sink that collects to a list."""

    async def get_data(self) -> List[Any]:
        """Get collected data."""
        return [r.data for r in self._records]


class FileDataSink(DataSink):
    """Sink that writes to a file."""

    def __init__(self, path: str, format: DataFormat = DataFormat.JSON):
        super().__init__()
        self.path = Path(path)
        self.format = format

    async def flush(self) -> None:
        """Flush to file."""
        data = [r.data for r in self._records]

        if self.format == DataFormat.JSON:
            self.path.write_text(json.dumps(data, indent=2))

        elif self.format == DataFormat.CSV:
            if data and isinstance(data[0], dict):
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                self.path.write_text(output.getvalue())

        elif self.format == DataFormat.TEXT:
            lines = [str(d) for d in data]
            self.path.write_text('\n'.join(lines))


# ============================================================================
# STREAM PROCESSOR
# ============================================================================

class StreamProcessor:
    """
    Process streaming data with windowing and aggregation.
    """

    def __init__(
        self,
        window_seconds: float = 10.0,
        slide_seconds: float = 5.0
    ):
        """Initialize stream processor."""
        self.window_seconds = window_seconds
        self.slide_seconds = slide_seconds
        self._buffer: List[Tuple[datetime, DataRecord]] = []
        self._handlers: List[Callable[[List[DataRecord]], Awaitable[None]]] = []

    def on_window(
        self,
        handler: Callable[[List[DataRecord]], Awaitable[None]]
    ) -> None:
        """Register a window handler."""
        self._handlers.append(handler)

    async def process(self, record: DataRecord) -> None:
        """Process a streaming record."""
        now = datetime.now()
        self._buffer.append((now, record))

        # Remove records outside window
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._buffer = [(t, r) for t, r in self._buffer if t >= cutoff]

    async def emit_window(self) -> None:
        """Emit current window to handlers."""
        records = [r for _, r in self._buffer]
        for handler in self._handlers:
            await handler(records)

    async def start(self) -> None:
        """Start window emission loop."""
        while True:
            await asyncio.sleep(self.slide_seconds)
            await self.emit_window()


# ============================================================================
# MAIN PIPELINE ENGINE
# ============================================================================

class DataPipelineEngine:
    """
    Main data pipeline execution engine.

    Features:
    - ETL pipeline execution
    - Parallel stage processing
    - Data validation
    - Error handling and recovery
    - Checkpointing
    - Metrics and monitoring

    "Through Ba'el's pipelines flows the essence of understanding." — Ba'el
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline engine."""
        self.config = config or PipelineConfig()

        # Pipeline registry
        self._pipelines: Dict[str, Pipeline] = {}

        # Running state
        self._running_pipelines: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_pipelines)

        # Quarantine for invalid records
        self._quarantine: Dict[str, List[DataRecord]] = defaultdict(list)

        # Statistics
        self._stats = {
            'pipelines_created': 0,
            'pipelines_completed': 0,
            'pipelines_failed': 0,
            'records_processed': 0,
            'records_quarantined': 0
        }

        logger.info("DataPipelineEngine initialized")

    # ========================================================================
    # PIPELINE CREATION
    # ========================================================================

    def create_pipeline(
        self,
        name: str,
        description: str = "",
        continue_on_error: bool = False,
        max_records: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> 'PipelineBuilder':
        """Create a new pipeline using fluent builder."""
        return PipelineBuilder(
            engine=self,
            name=name,
            description=description,
            continue_on_error=continue_on_error,
            max_records=max_records,
            tags=tags or []
        )

    def register_pipeline(self, pipeline: Pipeline) -> None:
        """Register a pipeline."""
        self._pipelines[pipeline.id] = pipeline
        self._stats['pipelines_created'] += 1
        logger.info(f"Registered pipeline: {pipeline.name} ({pipeline.id})")

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[Pipeline]:
        """List all pipelines."""
        return list(self._pipelines.values())

    # ========================================================================
    # PIPELINE EXECUTION
    # ========================================================================

    async def run(
        self,
        pipeline_id: str,
        source: DataSource,
        sink: Optional[DataSink] = None
    ) -> PipelineResult:
        """Run a pipeline."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        async with self._semaphore:
            return await self._execute_pipeline(pipeline, source, sink or ListDataSink())

    async def run_adhoc(
        self,
        stages: List[Stage],
        source: DataSource,
        sink: Optional[DataSink] = None,
        name: str = "adhoc"
    ) -> PipelineResult:
        """Run an ad-hoc pipeline without registration."""
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name=name,
            stages=stages
        )

        return await self._execute_pipeline(pipeline, source, sink or ListDataSink())

    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        source: DataSource,
        sink: DataSink
    ) -> PipelineResult:
        """Execute a pipeline."""
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now()

        stage_results = []
        total_input = 0
        total_output = 0
        total_errors = 0

        # Read source data
        records = await source.read_all()
        total_input = len(records)

        if pipeline.max_records:
            records = records[:pipeline.max_records]

        logger.info(f"Starting pipeline {pipeline.name} with {len(records)} records")

        try:
            # Execute stages
            for i, stage in enumerate(pipeline.stages):
                pipeline.current_stage_index = i

                stage_start = datetime.now()
                stage.status = StageStatus.RUNNING

                try:
                    records, stage_result = await self._execute_stage(
                        stage, records, pipeline
                    )
                    stage_results.append(stage_result)
                    total_errors += stage_result.error_count

                    if stage_result.status == StageStatus.FAILED and not pipeline.continue_on_error:
                        raise Exception(f"Stage {stage.name} failed")

                except Exception as e:
                    stage.status = StageStatus.FAILED
                    stage_result = StageResult(
                        stage_id=stage.id,
                        status=StageStatus.FAILED,
                        input_count=len(records),
                        output_count=0,
                        error_count=1,
                        started_at=stage_start,
                        completed_at=datetime.now(),
                        duration_ms=int((datetime.now() - stage_start).total_seconds() * 1000),
                        errors=[str(e)]
                    )
                    stage_results.append(stage_result)

                    if not pipeline.continue_on_error:
                        raise

            # Write to sink
            for record in records:
                await sink.write(record)
            await sink.flush()

            total_output = len(records)
            pipeline.status = PipelineStatus.COMPLETED
            self._stats['pipelines_completed'] += 1

        except Exception as e:
            pipeline.status = PipelineStatus.FAILED
            self._stats['pipelines_failed'] += 1
            logger.error(f"Pipeline {pipeline.name} failed: {e}")

        pipeline.completed_at = datetime.now()
        duration_ms = int((pipeline.completed_at - pipeline.started_at).total_seconds() * 1000)

        self._stats['records_processed'] += total_input

        return PipelineResult(
            pipeline_id=pipeline.id,
            status=pipeline.status,
            stages=stage_results,
            total_input=total_input,
            total_output=total_output,
            total_errors=total_errors,
            started_at=pipeline.started_at,
            completed_at=pipeline.completed_at,
            duration_ms=duration_ms
        )

    async def _execute_stage(
        self,
        stage: Stage,
        records: List[DataRecord],
        pipeline: Pipeline
    ) -> Tuple[List[DataRecord], StageResult]:
        """Execute a single stage."""
        stage_start = datetime.now()
        input_count = len(records)
        output_records = []
        errors = []

        logger.debug(f"Executing stage: {stage.name}")

        try:
            if stage.parallel:
                # Parallel execution
                output_records = await self._execute_parallel(stage, records)
            else:
                # Sequential execution
                output_records = await self._execute_sequential(stage, records)

            # Validation
            if stage.validation_level != ValidationLevel.NONE and stage.validator:
                output_records, invalid = self._validate_records(
                    output_records, stage, pipeline.id
                )
                if invalid:
                    errors.extend([f"Validation failed for {len(invalid)} records"])

            stage.status = StageStatus.COMPLETED

        except Exception as e:
            errors.append(str(e))
            stage.status = StageStatus.FAILED
            logger.error(f"Stage {stage.name} error: {e}")

        stage_end = datetime.now()
        duration_ms = int((stage_end - stage_start).total_seconds() * 1000)

        result = StageResult(
            stage_id=stage.id,
            status=stage.status,
            input_count=input_count,
            output_count=len(output_records),
            error_count=len(errors),
            started_at=stage_start,
            completed_at=stage_end,
            duration_ms=duration_ms,
            errors=errors
        )

        stage.result = result
        return output_records, result

    async def _execute_sequential(
        self,
        stage: Stage,
        records: List[DataRecord]
    ) -> List[DataRecord]:
        """Execute stage sequentially."""
        output = []

        for record in records:
            try:
                result = stage.transform(record)

                if result is None:
                    continue  # Filtered out
                elif isinstance(result, list):
                    output.extend(result)  # Flatmap
                else:
                    output.append(result)

            except Exception as e:
                record.errors.append(str(e))
                if stage.retry_count > 0:
                    # Retry logic
                    for attempt in range(stage.retry_count):
                        try:
                            await asyncio.sleep(stage.retry_delay_seconds * (attempt + 1))
                            result = stage.transform(record)
                            if result:
                                output.append(result)
                            break
                        except Exception:
                            continue

        return output

    async def _execute_parallel(
        self,
        stage: Stage,
        records: List[DataRecord]
    ) -> List[DataRecord]:
        """Execute stage in parallel batches."""
        output = []
        semaphore = asyncio.Semaphore(stage.max_workers)

        async def process_record(record: DataRecord) -> Optional[DataRecord]:
            async with semaphore:
                try:
                    return stage.transform(record)
                except Exception as e:
                    record.errors.append(str(e))
                    return None

        # Process in batches
        for i in range(0, len(records), stage.batch_size):
            batch = records[i:i + stage.batch_size]
            tasks = [process_record(r) for r in batch]
            results = await asyncio.gather(*tasks)

            for result in results:
                if result is None:
                    continue
                elif isinstance(result, list):
                    output.extend(result)
                else:
                    output.append(result)

        return output

    def _validate_records(
        self,
        records: List[DataRecord],
        stage: Stage,
        pipeline_id: str
    ) -> Tuple[List[DataRecord], List[DataRecord]]:
        """Validate records and handle invalid ones."""
        valid = []
        invalid = []

        for record in records:
            if stage.validator(record):
                valid.append(record)
            else:
                invalid.append(record)

                if stage.validation_level == ValidationLevel.QUARANTINE:
                    self._quarantine[pipeline_id].append(record)
                    self._stats['records_quarantined'] += 1
                elif stage.validation_level == ValidationLevel.WARN:
                    logger.warning(f"Invalid record: {record.id}")

        if stage.validation_level == ValidationLevel.STRICT and invalid:
            raise ValueError(f"{len(invalid)} records failed validation")

        return valid, invalid

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_quarantine(self, pipeline_id: str) -> List[DataRecord]:
        """Get quarantined records for a pipeline."""
        return self._quarantine.get(pipeline_id, [])

    def clear_quarantine(self, pipeline_id: str) -> int:
        """Clear quarantine for a pipeline."""
        count = len(self._quarantine.get(pipeline_id, []))
        self._quarantine[pipeline_id] = []
        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            'registered_pipelines': len(self._pipelines),
            'running_pipelines': len(self._running_pipelines),
            'quarantine_size': sum(len(q) for q in self._quarantine.values())
        }

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'statistics': self.get_statistics(),
            'pipelines': {
                p.id: {
                    'name': p.name,
                    'status': p.status.value,
                    'stages': len(p.stages)
                }
                for p in self._pipelines.values()
            }
        }


# ============================================================================
# PIPELINE BUILDER
# ============================================================================

class PipelineBuilder:
    """
    Fluent builder for creating pipelines.
    """

    def __init__(
        self,
        engine: DataPipelineEngine,
        name: str,
        description: str = "",
        continue_on_error: bool = False,
        max_records: Optional[int] = None,
        tags: Optional[List[str]] = None
    ):
        """Initialize builder."""
        self.engine = engine
        self.pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            continue_on_error=continue_on_error,
            max_records=max_records,
            stages=[],
            tags=tags or []
        )

    def add_stage(
        self,
        name: str,
        transform: Callable,
        transform_type: TransformType = TransformType.MAP,
        **kwargs
    ) -> 'PipelineBuilder':
        """Add a stage to the pipeline."""
        stage = Stage(
            id=str(uuid.uuid4()),
            name=name,
            transform_type=transform_type,
            transform=transform,
            **kwargs
        )
        self.pipeline.stages.append(stage)
        return self

    def map(self, func: Callable[[Any], Any], name: str = "map", **kwargs) -> 'PipelineBuilder':
        """Add a map stage."""
        return self.add_stage(name, Transform.map(func), TransformType.MAP, **kwargs)

    def filter(self, predicate: Callable[[Any], bool], name: str = "filter", **kwargs) -> 'PipelineBuilder':
        """Add a filter stage."""
        return self.add_stage(name, Transform.filter(predicate), TransformType.FILTER, **kwargs)

    def validate(
        self,
        validator: Callable[[DataRecord], bool],
        level: ValidationLevel = ValidationLevel.WARN,
        name: str = "validate"
    ) -> 'PipelineBuilder':
        """Add a validation stage."""
        def passthrough(record: DataRecord) -> DataRecord:
            return record

        stage = Stage(
            id=str(uuid.uuid4()),
            name=name,
            transform_type=TransformType.MAP,
            transform=passthrough,
            validation_level=level,
            validator=validator
        )
        self.pipeline.stages.append(stage)
        return self

    def flatten(self, name: str = "flatten", **kwargs) -> 'PipelineBuilder':
        """Add a flatten stage."""
        return self.add_stage(name, Transform.flatten(), TransformType.FLATMAP, **kwargs)

    def parallel(self, workers: int = 4) -> 'PipelineBuilder':
        """Make the last stage parallel."""
        if self.pipeline.stages:
            self.pipeline.stages[-1].parallel = True
            self.pipeline.stages[-1].max_workers = workers
        return self

    def with_retry(self, count: int = 3, delay: float = 1.0) -> 'PipelineBuilder':
        """Add retry to the last stage."""
        if self.pipeline.stages:
            self.pipeline.stages[-1].retry_count = count
            self.pipeline.stages[-1].retry_delay_seconds = delay
        return self

    def build(self) -> Pipeline:
        """Build and register the pipeline."""
        self.engine.register_pipeline(self.pipeline)
        return self.pipeline


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

pipeline_engine = DataPipelineEngine()
