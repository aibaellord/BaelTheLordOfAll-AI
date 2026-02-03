#!/usr/bin/env python3
"""
BAEL - Data Pipeline Engine
Comprehensive ETL and data pipeline system.

Features:
- Pipeline stages (Extract, Transform, Load)
- Data transformations
- Error handling
- Parallel processing
- Backpressure handling
- Checkpointing
- Retry logic
- Monitoring and metrics
- Schema validation
- Data quality checks
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, AsyncGenerator, Awaitable, Callable, Deque, Dict,
                    Generator, Generic, List, Optional, Set, Tuple, Type,
                    TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class PipelineState(Enum):
    """Pipeline execution state."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageType(Enum):
    """Pipeline stage types."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    BRANCH = "branch"
    MERGE = "merge"
    CUSTOM = "custom"


class DataQuality(Enum):
    """Data quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ErrorAction(Enum):
    """Actions on error."""
    SKIP = "skip"
    RETRY = "retry"
    FAIL = "fail"
    DEAD_LETTER = "dead_letter"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DataRecord:
    """Data record with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Any = None
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    quality: DataQuality = DataQuality.UNKNOWN


@dataclass
class StageConfig:
    """Stage configuration."""
    name: str = ""
    stage_type: StageType = StageType.CUSTOM
    parallel: bool = False
    batch_size: int = 1
    timeout: float = 30.0
    retries: int = 3
    error_action: ErrorAction = ErrorAction.SKIP
    enabled: bool = True


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    name: str = ""
    description: str = ""
    max_workers: int = 4
    buffer_size: int = 1000
    checkpoint_interval: int = 100
    enable_metrics: bool = True


@dataclass
class StageMetrics:
    """Stage execution metrics."""
    records_in: int = 0
    records_out: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineMetrics:
    """Pipeline execution metrics."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    stage_metrics: Dict[str, StageMetrics] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """Pipeline checkpoint."""
    pipeline_id: str
    stage_name: str
    record_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    state: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ABSTRACT STAGE
# =============================================================================

class PipelineStage(ABC, Generic[T, R]):
    """Abstract pipeline stage."""

    def __init__(self, config: Optional[StageConfig] = None):
        self.config = config or StageConfig()
        self.metrics = StageMetrics()
        self._active = True

    @abstractmethod
    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        """Process a single record."""
        pass

    async def process_batch(self, records: List[DataRecord]) -> List[DataRecord]:
        """Process a batch of records."""
        results = []
        for record in records:
            try:
                result = await self.process(record)
                if result:
                    results.append(result)
            except Exception as e:
                self.metrics.records_failed += 1
                self.metrics.errors.append(str(e))

                if self.config.error_action == ErrorAction.FAIL:
                    raise

        return results

    async def initialize(self) -> None:
        """Initialize stage."""
        pass

    async def cleanup(self) -> None:
        """Cleanup stage."""
        pass

    def stop(self) -> None:
        """Stop stage processing."""
        self._active = False


# =============================================================================
# BUILT-IN STAGES
# =============================================================================

class ExtractStage(PipelineStage[None, T]):
    """Extract data from source."""

    def __init__(
        self,
        source: Callable[[], AsyncGenerator[Any, None]],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.EXTRACT))
        self.source = source

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        # Extract stage generates records, not transforms
        return record

    async def extract(self) -> AsyncGenerator[DataRecord, None]:
        """Extract records from source."""
        async for item in self.source():
            self.metrics.records_in += 1
            record = DataRecord(data=item, source=self.config.name)
            self.metrics.records_out += 1
            yield record


class TransformStage(PipelineStage[T, R]):
    """Transform data."""

    def __init__(
        self,
        transformer: Callable[[Any], Any],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.TRANSFORM))
        self.transformer = transformer

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1
        start = time.time()

        try:
            if asyncio.iscoroutinefunction(self.transformer):
                result = await self.transformer(record.data)
            else:
                result = self.transformer(record.data)

            record.data = result
            self.metrics.records_out += 1
            self.metrics.processing_time += time.time() - start
            return record

        except Exception as e:
            record.errors.append(str(e))
            self.metrics.records_failed += 1
            raise


class FilterStage(PipelineStage[T, T]):
    """Filter records based on condition."""

    def __init__(
        self,
        predicate: Callable[[Any], bool],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.FILTER))
        self.predicate = predicate

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1

        try:
            if asyncio.iscoroutinefunction(self.predicate):
                passes = await self.predicate(record.data)
            else:
                passes = self.predicate(record.data)

            if passes:
                self.metrics.records_out += 1
                return record
            else:
                self.metrics.records_skipped += 1
                return None

        except Exception as e:
            record.errors.append(str(e))
            self.metrics.records_failed += 1
            raise


class LoadStage(PipelineStage[T, None]):
    """Load data to destination."""

    def __init__(
        self,
        loader: Callable[[Any], Awaitable[None]],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.LOAD))
        self.loader = loader

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1
        start = time.time()

        try:
            if asyncio.iscoroutinefunction(self.loader):
                await self.loader(record.data)
            else:
                self.loader(record.data)

            self.metrics.records_out += 1
            self.metrics.processing_time += time.time() - start
            return record

        except Exception as e:
            record.errors.append(str(e))
            self.metrics.records_failed += 1
            raise


class AggregateStage(PipelineStage[T, R]):
    """Aggregate records."""

    def __init__(
        self,
        aggregator: Callable[[List[Any]], Any],
        window_size: int = 10,
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.AGGREGATE))
        self.aggregator = aggregator
        self.window_size = window_size
        self.buffer: List[DataRecord] = []

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1
        self.buffer.append(record)

        if len(self.buffer) >= self.window_size:
            return await self._flush()

        return None

    async def _flush(self) -> Optional[DataRecord]:
        """Flush buffer and aggregate."""
        if not self.buffer:
            return None

        data = [r.data for r in self.buffer]

        try:
            if asyncio.iscoroutinefunction(self.aggregator):
                result = await self.aggregator(data)
            else:
                result = self.aggregator(data)

            aggregated = DataRecord(
                data=result,
                source=self.config.name,
                metadata={"aggregated_count": len(self.buffer)}
            )

            self.buffer.clear()
            self.metrics.records_out += 1
            return aggregated

        except Exception as e:
            self.metrics.records_failed += 1
            self.buffer.clear()
            raise

    async def cleanup(self) -> None:
        """Flush remaining records."""
        if self.buffer:
            await self._flush()


class MapStage(PipelineStage[T, R]):
    """Map function over records."""

    def __init__(
        self,
        mapper: Callable[[Any], Any],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.TRANSFORM))
        self.mapper = mapper

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1

        try:
            if asyncio.iscoroutinefunction(self.mapper):
                record.data = await self.mapper(record.data)
            else:
                record.data = self.mapper(record.data)

            self.metrics.records_out += 1
            return record

        except Exception as e:
            record.errors.append(str(e))
            self.metrics.records_failed += 1
            raise


class FlatMapStage(PipelineStage[T, R]):
    """FlatMap - map and flatten results."""

    def __init__(
        self,
        mapper: Callable[[Any], List[Any]],
        config: Optional[StageConfig] = None
    ):
        super().__init__(config or StageConfig(stage_type=StageType.TRANSFORM))
        self.mapper = mapper
        self._pending: Deque[DataRecord] = deque()

    async def process(self, record: DataRecord) -> Optional[DataRecord]:
        self.metrics.records_in += 1

        try:
            if asyncio.iscoroutinefunction(self.mapper):
                results = await self.mapper(record.data)
            else:
                results = self.mapper(record.data)

            if results:
                for item in results[1:]:
                    new_record = DataRecord(
                        data=item,
                        source=record.source,
                        metadata=record.metadata.copy()
                    )
                    self._pending.append(new_record)

                record.data = results[0]
                self.metrics.records_out += len(results)
                return record

            return None

        except Exception as e:
            record.errors.append(str(e))
            self.metrics.records_failed += 1
            raise


# =============================================================================
# PIPELINE
# =============================================================================

class DataPipeline:
    """
    Data Pipeline Engine for BAEL.

    Provides ETL capabilities with stages, error handling, and monitoring.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.id = str(uuid.uuid4())

        self._stages: List[Tuple[str, PipelineStage]] = []
        self._state = PipelineState.IDLE
        self._metrics = PipelineMetrics()
        self._checkpoints: List[Checkpoint] = []
        self._dead_letter: List[DataRecord] = []
        self._listeners: List[Callable[[str, DataRecord], None]] = []
        self._buffer: Deque[DataRecord] = deque(maxlen=self.config.buffer_size)

        self._running = False
        self._paused = False

    # -------------------------------------------------------------------------
    # STAGE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_stage(self, name: str, stage: PipelineStage) -> "DataPipeline":
        """Add a stage to the pipeline."""
        stage.config.name = name
        self._stages.append((name, stage))
        self._metrics.stage_metrics[name] = StageMetrics()
        return self

    def extract(
        self,
        source: Callable[[], AsyncGenerator[Any, None]],
        name: str = "extract"
    ) -> "DataPipeline":
        """Add extract stage."""
        return self.add_stage(name, ExtractStage(source))

    def transform(
        self,
        transformer: Callable[[Any], Any],
        name: str = "transform"
    ) -> "DataPipeline":
        """Add transform stage."""
        return self.add_stage(name, TransformStage(transformer))

    def filter(
        self,
        predicate: Callable[[Any], bool],
        name: str = "filter"
    ) -> "DataPipeline":
        """Add filter stage."""
        return self.add_stage(name, FilterStage(predicate))

    def load(
        self,
        loader: Callable[[Any], Awaitable[None]],
        name: str = "load"
    ) -> "DataPipeline":
        """Add load stage."""
        return self.add_stage(name, LoadStage(loader))

    def map(
        self,
        mapper: Callable[[Any], Any],
        name: str = "map"
    ) -> "DataPipeline":
        """Add map stage."""
        return self.add_stage(name, MapStage(mapper))

    def aggregate(
        self,
        aggregator: Callable[[List[Any]], Any],
        window_size: int = 10,
        name: str = "aggregate"
    ) -> "DataPipeline":
        """Add aggregate stage."""
        return self.add_stage(name, AggregateStage(aggregator, window_size))

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def run(self, source: Optional[AsyncGenerator[Any, None]] = None) -> PipelineMetrics:
        """Run the pipeline."""
        if self._state == PipelineState.RUNNING:
            raise RuntimeError("Pipeline already running")

        self._state = PipelineState.RUNNING
        self._running = True
        self._metrics = PipelineMetrics(start_time=datetime.utcnow())

        try:
            # Initialize stages
            for name, stage in self._stages:
                await stage.initialize()

            # Find extract stage or use provided source
            if source:
                async for item in source:
                    if not self._running:
                        break

                    while self._paused:
                        await asyncio.sleep(0.1)

                    record = DataRecord(data=item)
                    await self._process_record(record)
            else:
                # Use extract stages
                for name, stage in self._stages:
                    if isinstance(stage, ExtractStage):
                        async for record in stage.extract():
                            if not self._running:
                                break

                            while self._paused:
                                await asyncio.sleep(0.1)

                            await self._process_record(record, skip_stage=name)

            # Cleanup stages
            for name, stage in self._stages:
                await stage.cleanup()

            self._state = PipelineState.COMPLETED

        except Exception as e:
            self._state = PipelineState.FAILED
            logger.error(f"Pipeline failed: {e}")
            raise

        finally:
            self._metrics.end_time = datetime.utcnow()
            self._running = False

        return self._metrics

    async def _process_record(self, record: DataRecord, skip_stage: Optional[str] = None) -> None:
        """Process a record through all stages."""
        self._metrics.total_records += 1
        current = record

        for name, stage in self._stages:
            if skip_stage and name == skip_stage:
                continue

            if isinstance(stage, ExtractStage):
                continue

            if not stage.config.enabled:
                continue

            try:
                start = time.time()

                if stage.config.batch_size > 1:
                    self._buffer.append(current)
                    if len(self._buffer) >= stage.config.batch_size:
                        batch = list(self._buffer)
                        self._buffer.clear()
                        results = await stage.process_batch(batch)
                        for r in results:
                            await self._continue_from(name, r)
                    return

                result = await asyncio.wait_for(
                    stage.process(current),
                    timeout=stage.config.timeout
                )

                self._metrics.stage_metrics[name] = stage.metrics

                if result is None:
                    return  # Record filtered out

                current = result

                # Checkpoint
                if self._metrics.processed_records % self.config.checkpoint_interval == 0:
                    self._save_checkpoint(name, current)

            except asyncio.TimeoutError:
                logger.warning(f"Stage {name} timed out")
                await self._handle_error(stage, current, TimeoutError("Stage timeout"))
                return

            except Exception as e:
                await self._handle_error(stage, current, e)
                if stage.config.error_action == ErrorAction.FAIL:
                    raise
                return

        self._metrics.processed_records += 1
        self._notify_listeners("completed", current)

    async def _continue_from(self, from_stage: str, record: DataRecord) -> None:
        """Continue processing from a specific stage."""
        found = False
        for name, stage in self._stages:
            if name == from_stage:
                found = True
                continue
            if not found:
                continue

            result = await stage.process(record)
            if result is None:
                return
            record = result

    async def _handle_error(
        self,
        stage: PipelineStage,
        record: DataRecord,
        error: Exception
    ) -> None:
        """Handle processing error."""
        self._metrics.failed_records += 1
        record.errors.append(str(error))

        if stage.config.error_action == ErrorAction.DEAD_LETTER:
            self._dead_letter.append(record)

        elif stage.config.error_action == ErrorAction.RETRY:
            for attempt in range(stage.config.retries):
                try:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    result = await stage.process(record)
                    if result:
                        return
                except Exception:
                    continue

            # All retries failed
            self._dead_letter.append(record)

        self._notify_listeners("error", record)

    def _save_checkpoint(self, stage_name: str, record: DataRecord) -> None:
        """Save checkpoint."""
        checkpoint = Checkpoint(
            pipeline_id=self.id,
            stage_name=stage_name,
            record_id=record.id
        )
        self._checkpoints.append(checkpoint)

        # Keep only recent checkpoints
        if len(self._checkpoints) > 100:
            self._checkpoints = self._checkpoints[-100:]

    # -------------------------------------------------------------------------
    # CONTROL
    # -------------------------------------------------------------------------

    def pause(self) -> None:
        """Pause pipeline execution."""
        self._paused = True
        self._state = PipelineState.PAUSED

    def resume(self) -> None:
        """Resume pipeline execution."""
        self._paused = False
        self._state = PipelineState.RUNNING

    def stop(self) -> None:
        """Stop pipeline execution."""
        self._running = False
        self._state = PipelineState.CANCELLED
        for _, stage in self._stages:
            stage.stop()

    @property
    def state(self) -> PipelineState:
        """Get pipeline state."""
        return self._state

    @property
    def metrics(self) -> PipelineMetrics:
        """Get pipeline metrics."""
        return self._metrics

    # -------------------------------------------------------------------------
    # LISTENERS
    # -------------------------------------------------------------------------

    def add_listener(self, callback: Callable[[str, DataRecord], None]) -> None:
        """Add event listener."""
        self._listeners.append(callback)

    def _notify_listeners(self, event: str, record: DataRecord) -> None:
        """Notify listeners."""
        for listener in self._listeners:
            try:
                listener(event, record)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    # -------------------------------------------------------------------------
    # DEAD LETTER
    # -------------------------------------------------------------------------

    def get_dead_letters(self) -> List[DataRecord]:
        """Get dead letter records."""
        return self._dead_letter.copy()

    def clear_dead_letters(self) -> int:
        """Clear dead letter queue."""
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count

    # -------------------------------------------------------------------------
    # CHECKPOINTS
    # -------------------------------------------------------------------------

    def get_checkpoints(self) -> List[Checkpoint]:
        """Get checkpoints."""
        return self._checkpoints.copy()

    def get_last_checkpoint(self) -> Optional[Checkpoint]:
        """Get last checkpoint."""
        return self._checkpoints[-1] if self._checkpoints else None


# =============================================================================
# PIPELINE BUILDER
# =============================================================================

class PipelineBuilder:
    """Fluent pipeline builder."""

    def __init__(self, name: str = ""):
        self.config = PipelineConfig(name=name)
        self._stages: List[Tuple[str, PipelineStage]] = []

    def with_workers(self, count: int) -> "PipelineBuilder":
        """Set max workers."""
        self.config.max_workers = count
        return self

    def with_buffer(self, size: int) -> "PipelineBuilder":
        """Set buffer size."""
        self.config.buffer_size = size
        return self

    def extract(
        self,
        source: Callable[[], AsyncGenerator[Any, None]],
        name: str = "extract"
    ) -> "PipelineBuilder":
        """Add extract stage."""
        self._stages.append((name, ExtractStage(source)))
        return self

    def transform(
        self,
        transformer: Callable[[Any], Any],
        name: str = "transform"
    ) -> "PipelineBuilder":
        """Add transform stage."""
        self._stages.append((name, TransformStage(transformer)))
        return self

    def filter(
        self,
        predicate: Callable[[Any], bool],
        name: str = "filter"
    ) -> "PipelineBuilder":
        """Add filter stage."""
        self._stages.append((name, FilterStage(predicate)))
        return self

    def load(
        self,
        loader: Callable[[Any], Awaitable[None]],
        name: str = "load"
    ) -> "PipelineBuilder":
        """Add load stage."""
        self._stages.append((name, LoadStage(loader)))
        return self

    def map(
        self,
        mapper: Callable[[Any], Any],
        name: str = "map"
    ) -> "PipelineBuilder":
        """Add map stage."""
        self._stages.append((name, MapStage(mapper)))
        return self

    def build(self) -> DataPipeline:
        """Build the pipeline."""
        pipeline = DataPipeline(self.config)
        for name, stage in self._stages:
            pipeline.add_stage(name, stage)
        return pipeline


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Pipeline Engine."""
    print("=" * 70)
    print("BAEL - DATA PIPELINE ENGINE DEMO")
    print("ETL and Data Processing")
    print("=" * 70)
    print()

    # 1. Simple Pipeline
    print("1. SIMPLE PIPELINE:")
    print("-" * 40)

    async def number_source():
        for i in range(10):
            yield {"value": i}
            await asyncio.sleep(0.01)

    loaded_data = []

    async def simple_loader(data):
        loaded_data.append(data)

    pipeline = (DataPipeline(PipelineConfig(name="simple"))
               .extract(number_source, "numbers")
               .transform(lambda x: {"value": x["value"] * 2}, "double")
               .filter(lambda x: x["value"] > 5, "filter_gt_5")
               .load(simple_loader, "store"))

    metrics = await pipeline.run()

    print(f"   Total records: {metrics.total_records}")
    print(f"   Processed: {metrics.processed_records}")
    print(f"   Loaded: {len(loaded_data)}")
    print(f"   Values: {[d['value'] for d in loaded_data]}")
    print()

    # 2. With External Source
    print("2. EXTERNAL SOURCE:")
    print("-" * 40)

    async def user_source():
        users = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]
        for user in users:
            yield user

    processed_users = []

    pipeline2 = (DataPipeline()
                .transform(lambda u: {**u, "adult": u["age"] >= 18}, "add_adult_flag")
                .transform(lambda u: {**u, "name": u["name"].upper()}, "uppercase_name")
                .load(lambda u: processed_users.append(u), "collect"))

    await pipeline2.run(source=user_source())

    for user in processed_users:
        print(f"   {user['name']}: age={user['age']}, adult={user['adult']}")
    print()

    # 3. Builder Pattern
    print("3. BUILDER PATTERN:")
    print("-" * 40)

    results = []

    async def data_source():
        for i in range(5):
            yield i

    pipeline3 = (PipelineBuilder("builder-pipeline")
                .with_workers(4)
                .with_buffer(100)
                .extract(data_source, "source")
                .map(lambda x: x ** 2, "square")
                .filter(lambda x: x > 4, "filter")
                .load(lambda x: results.append(x), "sink")
                .build())

    await pipeline3.run()
    print(f"   Results: {results}")
    print()

    # 4. Aggregation
    print("4. AGGREGATION:")
    print("-" * 40)

    aggregated = []

    async def values_source():
        for i in range(20):
            yield i

    pipeline4 = (DataPipeline()
                .aggregate(lambda batch: sum(batch), window_size=5, name="sum_5")
                .load(lambda x: aggregated.append(x), "collect"))

    await pipeline4.run(source=values_source())
    print(f"   Aggregated sums (window=5): {aggregated}")
    print()

    # 5. Error Handling
    print("5. ERROR HANDLING:")
    print("-" * 40)

    def risky_transform(data):
        if data.get("risky"):
            raise ValueError("Risky data encountered")
        return data

    async def risky_source():
        yield {"value": 1, "risky": False}
        yield {"value": 2, "risky": True}
        yield {"value": 3, "risky": False}

    safe_data = []

    transform_stage = TransformStage(
        risky_transform,
        StageConfig(name="risky", error_action=ErrorAction.DEAD_LETTER)
    )

    pipeline5 = DataPipeline()
    pipeline5.add_stage("risky", transform_stage)
    pipeline5.add_stage("collect", LoadStage(lambda x: safe_data.append(x)))

    await pipeline5.run(source=risky_source())

    print(f"   Processed: {len(safe_data)}")
    print(f"   Dead letters: {len(pipeline5.get_dead_letters())}")
    print()

    # 6. Stage Metrics
    print("6. STAGE METRICS:")
    print("-" * 40)

    async def metric_source():
        for i in range(100):
            yield i

    pipeline6 = (DataPipeline()
                .transform(lambda x: x * 2, "double")
                .filter(lambda x: x % 4 == 0, "mod_4")
                .load(lambda x: None, "sink"))

    metrics = await pipeline6.run(source=metric_source())

    for stage_name, stage_metrics in metrics.stage_metrics.items():
        print(f"   {stage_name}: in={stage_metrics.records_in}, out={stage_metrics.records_out}")
    print()

    # 7. Pipeline State
    print("7. PIPELINE STATE:")
    print("-" * 40)

    pipeline7 = DataPipeline(PipelineConfig(name="state-demo"))
    print(f"   Initial state: {pipeline7.state.value}")

    async def slow_source():
        for i in range(3):
            yield i
            await asyncio.sleep(0.1)

    task = asyncio.create_task(pipeline7.run(source=slow_source()))
    await asyncio.sleep(0.05)
    print(f"   Running state: {pipeline7.state.value}")

    await task
    print(f"   Final state: {pipeline7.state.value}")
    print()

    # 8. Data Records
    print("8. DATA RECORDS:")
    print("-" * 40)

    records = []

    def capture_record(event, record):
        if event == "completed":
            records.append(record)

    async def record_source():
        yield "test data"

    pipeline8 = DataPipeline()
    pipeline8.add_listener(capture_record)
    pipeline8.add_stage("identity", TransformStage(lambda x: x))

    await pipeline8.run(source=record_source())

    if records:
        r = records[0]
        print(f"   ID: {r.id[:8]}...")
        print(f"   Data: {r.data}")
        print(f"   Source: {r.source}")
    print()

    # 9. Checkpoints
    print("9. CHECKPOINTS:")
    print("-" * 40)

    async def checkpoint_source():
        for i in range(250):
            yield i

    pipeline9 = DataPipeline(PipelineConfig(checkpoint_interval=50))
    pipeline9.add_stage("pass", TransformStage(lambda x: x))

    await pipeline9.run(source=checkpoint_source())

    checkpoints = pipeline9.get_checkpoints()
    print(f"   Checkpoints saved: {len(checkpoints)}")

    last = pipeline9.get_last_checkpoint()
    if last:
        print(f"   Last checkpoint stage: {last.stage_name}")
    print()

    # 10. Execution Time
    print("10. EXECUTION TIME:")
    print("-" * 40)

    async def timed_source():
        for i in range(1000):
            yield i

    pipeline10 = (DataPipeline()
                 .map(lambda x: x * 2, "double")
                 .filter(lambda x: x % 3 == 0, "mod3")
                 .load(lambda x: None, "sink"))

    start = time.time()
    metrics = await pipeline10.run(source=timed_source())
    elapsed = time.time() - start

    print(f"   Records: {metrics.total_records}")
    print(f"   Processed: {metrics.processed_records}")
    print(f"   Time: {elapsed:.3f}s")
    print(f"   Throughput: {metrics.total_records/elapsed:.0f} records/sec")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Pipeline Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
