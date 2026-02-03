#!/usr/bin/env python3
"""
BAEL - Transformation Engine
Data transformation and processing pipelines for agents.

Features:
- Data transformations
- Pipeline composition
- Schema mapping
- Format conversion
- Stream processing
"""

import asyncio
import base64
import hashlib
import json
import math
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple,
    Type, TypeVar, Union
)


T = TypeVar('T')
U = TypeVar('U')


# =============================================================================
# ENUMS
# =============================================================================

class TransformType(Enum):
    """Types of transformations."""
    MAP = "map"
    FILTER = "filter"
    REDUCE = "reduce"
    FLATTEN = "flatten"
    GROUP = "group"
    SORT = "sort"
    AGGREGATE = "aggregate"
    CUSTOM = "custom"


class DataFormat(Enum):
    """Data formats."""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    YAML = "yaml"
    TEXT = "text"
    BINARY = "binary"


class SchemaType(Enum):
    """Schema types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class PipelineStatus(Enum):
    """Pipeline statuses."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamMode(Enum):
    """Stream processing modes."""
    BATCH = "batch"
    STREAMING = "streaming"
    MICRO_BATCH = "micro_batch"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Transform:
    """A transformation operation."""
    transform_id: str = ""
    name: str = ""
    transform_type: TransformType = TransformType.MAP
    function: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.transform_id:
            self.transform_id = str(uuid.uuid4())[:8]


@dataclass
class SchemaField:
    """A field in a schema."""
    name: str = ""
    field_type: SchemaType = SchemaType.STRING
    required: bool = True
    default: Any = None
    transformer: Optional[Callable] = None


@dataclass
class Schema:
    """A data schema."""
    schema_id: str = ""
    name: str = ""
    fields: List[SchemaField] = field(default_factory=list)

    def __post_init__(self):
        if not self.schema_id:
            self.schema_id = str(uuid.uuid4())[:8]


@dataclass
class Pipeline:
    """A transformation pipeline."""
    pipeline_id: str = ""
    name: str = ""
    transforms: List[Transform] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.IDLE
    input_schema: Optional[Schema] = None
    output_schema: Optional[Schema] = None

    def __post_init__(self):
        if not self.pipeline_id:
            self.pipeline_id = str(uuid.uuid4())[:8]


@dataclass
class TransformResult:
    """Result of a transformation."""
    result_id: str = ""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    records_in: int = 0
    records_out: int = 0
    duration: float = 0.0

    def __post_init__(self):
        if not self.result_id:
            self.result_id = str(uuid.uuid4())[:8]


@dataclass
class TransformConfig:
    """Transformation engine configuration."""
    batch_size: int = 1000
    stream_mode: StreamMode = StreamMode.BATCH
    max_workers: int = 4


# =============================================================================
# TRANSFORMER
# =============================================================================

class Transformer(ABC):
    """Base transformer class."""

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Transform data."""
        pass


class MapTransformer(Transformer):
    """Map transformation."""

    def __init__(self, function: Callable):
        self._function = function

    def transform(self, data: List[Any]) -> List[Any]:
        """Apply map transformation."""
        return [self._function(item) for item in data]


class FilterTransformer(Transformer):
    """Filter transformation."""

    def __init__(self, predicate: Callable):
        self._predicate = predicate

    def transform(self, data: List[Any]) -> List[Any]:
        """Apply filter transformation."""
        return [item for item in data if self._predicate(item)]


class ReduceTransformer(Transformer):
    """Reduce transformation."""

    def __init__(self, function: Callable, initial: Any = None):
        self._function = function
        self._initial = initial

    def transform(self, data: List[Any]) -> Any:
        """Apply reduce transformation."""
        if not data:
            return self._initial

        result = self._initial if self._initial is not None else data[0]
        start = 0 if self._initial is not None else 1

        for item in data[start:]:
            result = self._function(result, item)

        return result


class FlattenTransformer(Transformer):
    """Flatten nested lists."""

    def __init__(self, depth: int = 1):
        self._depth = depth

    def transform(self, data: List[Any]) -> List[Any]:
        """Flatten nested lists."""
        return self._flatten(data, self._depth)

    def _flatten(self, data: List[Any], depth: int) -> List[Any]:
        result = []

        for item in data:
            if isinstance(item, list) and depth > 0:
                result.extend(self._flatten(item, depth - 1))
            else:
                result.append(item)

        return result


class GroupTransformer(Transformer):
    """Group by transformation."""

    def __init__(self, key_func: Callable):
        self._key_func = key_func

    def transform(self, data: List[Any]) -> Dict[Any, List[Any]]:
        """Group items by key."""
        result = defaultdict(list)

        for item in data:
            key = self._key_func(item)
            result[key].append(item)

        return dict(result)


class SortTransformer(Transformer):
    """Sort transformation."""

    def __init__(self, key_func: Optional[Callable] = None, reverse: bool = False):
        self._key_func = key_func
        self._reverse = reverse

    def transform(self, data: List[Any]) -> List[Any]:
        """Sort items."""
        return sorted(data, key=self._key_func, reverse=self._reverse)


class AggregateTransformer(Transformer):
    """Aggregate transformation."""

    def __init__(
        self,
        aggregation: AggregationType,
        field: Optional[str] = None
    ):
        self._aggregation = aggregation
        self._field = field

    def transform(self, data: List[Any]) -> Any:
        """Aggregate items."""
        if not data:
            return None

        if self._field:
            values = [item.get(self._field) if isinstance(item, dict) else getattr(item, self._field, None)
                     for item in data]
            values = [v for v in values if v is not None]
        else:
            values = data

        if not values:
            return None

        if self._aggregation == AggregationType.SUM:
            return sum(values)
        elif self._aggregation == AggregationType.AVG:
            return sum(values) / len(values)
        elif self._aggregation == AggregationType.MIN:
            return min(values)
        elif self._aggregation == AggregationType.MAX:
            return max(values)
        elif self._aggregation == AggregationType.COUNT:
            return len(values)
        elif self._aggregation == AggregationType.FIRST:
            return values[0]
        elif self._aggregation == AggregationType.LAST:
            return values[-1]

        return None


# =============================================================================
# FORMAT CONVERTER
# =============================================================================

class FormatConverter:
    """Convert between data formats."""

    def to_json(self, data: Any) -> str:
        """Convert to JSON."""
        return json.dumps(data, default=str)

    def from_json(self, text: str) -> Any:
        """Parse JSON."""
        return json.loads(text)

    def to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert to CSV."""
        if not data:
            return ""

        headers = list(data[0].keys())
        lines = [",".join(headers)]

        for row in data:
            values = [str(row.get(h, "")) for h in headers]
            lines.append(",".join(values))

        return "\n".join(lines)

    def from_csv(self, text: str) -> List[Dict[str, Any]]:
        """Parse CSV."""
        lines = text.strip().split("\n")

        if not lines:
            return []

        headers = lines[0].split(",")
        result = []

        for line in lines[1:]:
            values = line.split(",")
            row = dict(zip(headers, values))
            result.append(row)

        return result

    def to_base64(self, data: bytes) -> str:
        """Encode to base64."""
        return base64.b64encode(data).decode('utf-8')

    def from_base64(self, text: str) -> bytes:
        """Decode from base64."""
        return base64.b64decode(text)

    def convert(
        self,
        data: Any,
        from_format: DataFormat,
        to_format: DataFormat
    ) -> Any:
        """Convert between formats."""
        if from_format == DataFormat.JSON:
            intermediate = self.from_json(data) if isinstance(data, str) else data
        elif from_format == DataFormat.CSV:
            intermediate = self.from_csv(data)
        else:
            intermediate = data

        if to_format == DataFormat.JSON:
            return self.to_json(intermediate)
        elif to_format == DataFormat.CSV:
            return self.to_csv(intermediate)

        return intermediate


# =============================================================================
# SCHEMA MAPPER
# =============================================================================

class SchemaMapper:
    """Map data between schemas."""

    def __init__(self):
        self._mappings: Dict[str, Dict[str, str]] = {}

    def add_mapping(
        self,
        name: str,
        field_mappings: Dict[str, str]
    ) -> None:
        """Add a field mapping."""
        self._mappings[name] = field_mappings

    def map(
        self,
        data: Dict[str, Any],
        mapping_name: str
    ) -> Dict[str, Any]:
        """Map data using named mapping."""
        mapping = self._mappings.get(mapping_name, {})
        result = {}

        for target_field, source_field in mapping.items():
            if "." in source_field:
                value = self._get_nested(data, source_field)
            else:
                value = data.get(source_field)

            if value is not None:
                result[target_field] = value

        return result

    def map_list(
        self,
        data: List[Dict[str, Any]],
        mapping_name: str
    ) -> List[Dict[str, Any]]:
        """Map list of records."""
        return [self.map(item, mapping_name) for item in data]

    def _get_nested(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested field value."""
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current

    def validate(
        self,
        data: Dict[str, Any],
        schema: Schema
    ) -> Tuple[bool, List[str]]:
        """Validate data against schema."""
        errors = []

        for field in schema.fields:
            value = data.get(field.name)

            if value is None:
                if field.required and field.default is None:
                    errors.append(f"Missing required field: {field.name}")
                continue

            if not self._check_type(value, field.field_type):
                errors.append(f"Invalid type for {field.name}: expected {field.field_type.value}")

        return len(errors) == 0, errors

    def _check_type(self, value: Any, expected: SchemaType) -> bool:
        """Check if value matches expected type."""
        if expected == SchemaType.ANY:
            return True
        elif expected == SchemaType.STRING:
            return isinstance(value, str)
        elif expected == SchemaType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected == SchemaType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected == SchemaType.BOOLEAN:
            return isinstance(value, bool)
        elif expected == SchemaType.LIST:
            return isinstance(value, list)
        elif expected == SchemaType.DICT:
            return isinstance(value, dict)

        return False

    def apply_defaults(
        self,
        data: Dict[str, Any],
        schema: Schema
    ) -> Dict[str, Any]:
        """Apply default values from schema."""
        result = dict(data)

        for field in schema.fields:
            if field.name not in result and field.default is not None:
                result[field.name] = field.default

        return result


# =============================================================================
# PIPELINE BUILDER
# =============================================================================

class PipelineBuilder:
    """Build transformation pipelines."""

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}

    def create(self, name: str) -> Pipeline:
        """Create a pipeline."""
        pipeline = Pipeline(name=name)
        self._pipelines[pipeline.pipeline_id] = pipeline
        return pipeline

    def add_map(
        self,
        pipeline_id: str,
        name: str,
        function: Callable
    ) -> Optional[Transform]:
        """Add map transform."""
        return self._add_transform(
            pipeline_id,
            name,
            TransformType.MAP,
            function
        )

    def add_filter(
        self,
        pipeline_id: str,
        name: str,
        predicate: Callable
    ) -> Optional[Transform]:
        """Add filter transform."""
        return self._add_transform(
            pipeline_id,
            name,
            TransformType.FILTER,
            predicate
        )

    def add_reduce(
        self,
        pipeline_id: str,
        name: str,
        function: Callable,
        initial: Any = None
    ) -> Optional[Transform]:
        """Add reduce transform."""
        transform = self._add_transform(
            pipeline_id,
            name,
            TransformType.REDUCE,
            function
        )

        if transform:
            transform.config["initial"] = initial

        return transform

    def add_flatten(
        self,
        pipeline_id: str,
        name: str,
        depth: int = 1
    ) -> Optional[Transform]:
        """Add flatten transform."""
        transform = self._add_transform(
            pipeline_id,
            name,
            TransformType.FLATTEN,
            None
        )

        if transform:
            transform.config["depth"] = depth

        return transform

    def add_group(
        self,
        pipeline_id: str,
        name: str,
        key_func: Callable
    ) -> Optional[Transform]:
        """Add group transform."""
        return self._add_transform(
            pipeline_id,
            name,
            TransformType.GROUP,
            key_func
        )

    def add_sort(
        self,
        pipeline_id: str,
        name: str,
        key_func: Optional[Callable] = None,
        reverse: bool = False
    ) -> Optional[Transform]:
        """Add sort transform."""
        transform = self._add_transform(
            pipeline_id,
            name,
            TransformType.SORT,
            key_func
        )

        if transform:
            transform.config["reverse"] = reverse

        return transform

    def add_aggregate(
        self,
        pipeline_id: str,
        name: str,
        aggregation: AggregationType,
        field: Optional[str] = None
    ) -> Optional[Transform]:
        """Add aggregate transform."""
        transform = self._add_transform(
            pipeline_id,
            name,
            TransformType.AGGREGATE,
            None
        )

        if transform:
            transform.config["aggregation"] = aggregation
            transform.config["field"] = field

        return transform

    def _add_transform(
        self,
        pipeline_id: str,
        name: str,
        transform_type: TransformType,
        function: Optional[Callable]
    ) -> Optional[Transform]:
        """Add a transform to pipeline."""
        pipeline = self._pipelines.get(pipeline_id)

        if not pipeline:
            return None

        transform = Transform(
            name=name,
            transform_type=transform_type,
            function=function
        )

        pipeline.transforms.append(transform)

        return transform

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID."""
        return self._pipelines.get(pipeline_id)

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline."""
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            return True
        return False

    def count(self) -> int:
        """Count pipelines."""
        return len(self._pipelines)


# =============================================================================
# PIPELINE EXECUTOR
# =============================================================================

class PipelineExecutor:
    """Execute transformation pipelines."""

    def __init__(self, config: TransformConfig):
        self._config = config

    def execute(
        self,
        pipeline: Pipeline,
        data: Any
    ) -> TransformResult:
        """Execute a pipeline."""
        start_time = time.time()

        records_in = len(data) if isinstance(data, list) else 1

        pipeline.status = PipelineStatus.RUNNING
        current_data = data

        try:
            for transform in pipeline.transforms:
                transformer = self._create_transformer(transform)
                current_data = transformer.transform(current_data)

            pipeline.status = PipelineStatus.COMPLETED

            records_out = len(current_data) if isinstance(current_data, list) else 1

            return TransformResult(
                success=True,
                data=current_data,
                records_in=records_in,
                records_out=records_out,
                duration=time.time() - start_time
            )

        except Exception as e:
            pipeline.status = PipelineStatus.FAILED

            return TransformResult(
                success=False,
                error=str(e),
                records_in=records_in,
                duration=time.time() - start_time
            )

    def _create_transformer(self, transform: Transform) -> Transformer:
        """Create transformer from transform definition."""
        if transform.transform_type == TransformType.MAP:
            return MapTransformer(transform.function)

        elif transform.transform_type == TransformType.FILTER:
            return FilterTransformer(transform.function)

        elif transform.transform_type == TransformType.REDUCE:
            return ReduceTransformer(
                transform.function,
                transform.config.get("initial")
            )

        elif transform.transform_type == TransformType.FLATTEN:
            return FlattenTransformer(transform.config.get("depth", 1))

        elif transform.transform_type == TransformType.GROUP:
            return GroupTransformer(transform.function)

        elif transform.transform_type == TransformType.SORT:
            return SortTransformer(
                transform.function,
                transform.config.get("reverse", False)
            )

        elif transform.transform_type == TransformType.AGGREGATE:
            return AggregateTransformer(
                transform.config.get("aggregation", AggregationType.COUNT),
                transform.config.get("field")
            )

        raise ValueError(f"Unknown transform type: {transform.transform_type}")

    async def execute_async(
        self,
        pipeline: Pipeline,
        data: Any
    ) -> TransformResult:
        """Execute pipeline asynchronously."""
        return self.execute(pipeline, data)


# =============================================================================
# TRANSFORMATION ENGINE
# =============================================================================

class TransformationEngine:
    """
    Transformation Engine for BAEL.

    Data transformation and processing pipelines.
    """

    def __init__(self, config: Optional[TransformConfig] = None):
        self._config = config or TransformConfig()

        self._pipeline_builder = PipelineBuilder()
        self._pipeline_executor = PipelineExecutor(self._config)
        self._format_converter = FormatConverter()
        self._schema_mapper = SchemaMapper()

    # ----- Pipeline Operations -----

    def create_pipeline(self, name: str) -> Pipeline:
        """Create a pipeline."""
        return self._pipeline_builder.create(name)

    def add_map(
        self,
        pipeline_id: str,
        name: str,
        function: Callable
    ) -> Optional[Transform]:
        """Add map transform."""
        return self._pipeline_builder.add_map(pipeline_id, name, function)

    def add_filter(
        self,
        pipeline_id: str,
        name: str,
        predicate: Callable
    ) -> Optional[Transform]:
        """Add filter transform."""
        return self._pipeline_builder.add_filter(pipeline_id, name, predicate)

    def add_reduce(
        self,
        pipeline_id: str,
        name: str,
        function: Callable,
        initial: Any = None
    ) -> Optional[Transform]:
        """Add reduce transform."""
        return self._pipeline_builder.add_reduce(pipeline_id, name, function, initial)

    def add_flatten(
        self,
        pipeline_id: str,
        name: str,
        depth: int = 1
    ) -> Optional[Transform]:
        """Add flatten transform."""
        return self._pipeline_builder.add_flatten(pipeline_id, name, depth)

    def add_group(
        self,
        pipeline_id: str,
        name: str,
        key_func: Callable
    ) -> Optional[Transform]:
        """Add group transform."""
        return self._pipeline_builder.add_group(pipeline_id, name, key_func)

    def add_sort(
        self,
        pipeline_id: str,
        name: str,
        key_func: Optional[Callable] = None,
        reverse: bool = False
    ) -> Optional[Transform]:
        """Add sort transform."""
        return self._pipeline_builder.add_sort(pipeline_id, name, key_func, reverse)

    def add_aggregate(
        self,
        pipeline_id: str,
        name: str,
        aggregation: AggregationType,
        field: Optional[str] = None
    ) -> Optional[Transform]:
        """Add aggregate transform."""
        return self._pipeline_builder.add_aggregate(pipeline_id, name, aggregation, field)

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID."""
        return self._pipeline_builder.get_pipeline(pipeline_id)

    def execute(
        self,
        pipeline_id: str,
        data: Any
    ) -> TransformResult:
        """Execute a pipeline."""
        pipeline = self._pipeline_builder.get_pipeline(pipeline_id)

        if not pipeline:
            return TransformResult(
                success=False,
                error="Pipeline not found"
            )

        return self._pipeline_executor.execute(pipeline, data)

    async def execute_async(
        self,
        pipeline_id: str,
        data: Any
    ) -> TransformResult:
        """Execute pipeline asynchronously."""
        pipeline = self._pipeline_builder.get_pipeline(pipeline_id)

        if not pipeline:
            return TransformResult(
                success=False,
                error="Pipeline not found"
            )

        return await self._pipeline_executor.execute_async(pipeline, data)

    # ----- Format Conversion -----

    def to_json(self, data: Any) -> str:
        """Convert to JSON."""
        return self._format_converter.to_json(data)

    def from_json(self, text: str) -> Any:
        """Parse JSON."""
        return self._format_converter.from_json(text)

    def to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert to CSV."""
        return self._format_converter.to_csv(data)

    def from_csv(self, text: str) -> List[Dict[str, Any]]:
        """Parse CSV."""
        return self._format_converter.from_csv(text)

    def convert_format(
        self,
        data: Any,
        from_format: DataFormat,
        to_format: DataFormat
    ) -> Any:
        """Convert between formats."""
        return self._format_converter.convert(data, from_format, to_format)

    # ----- Schema Operations -----

    def add_mapping(
        self,
        name: str,
        field_mappings: Dict[str, str]
    ) -> None:
        """Add a schema mapping."""
        self._schema_mapper.add_mapping(name, field_mappings)

    def map_schema(
        self,
        data: Dict[str, Any],
        mapping_name: str
    ) -> Dict[str, Any]:
        """Map data using schema mapping."""
        return self._schema_mapper.map(data, mapping_name)

    def map_schema_list(
        self,
        data: List[Dict[str, Any]],
        mapping_name: str
    ) -> List[Dict[str, Any]]:
        """Map list using schema mapping."""
        return self._schema_mapper.map_list(data, mapping_name)

    def create_schema(
        self,
        name: str,
        fields: List[Tuple[str, SchemaType, bool, Any]]
    ) -> Schema:
        """Create a schema."""
        schema_fields = []

        for field_data in fields:
            field_name, field_type, required, default = field_data
            schema_fields.append(SchemaField(
                name=field_name,
                field_type=field_type,
                required=required,
                default=default
            ))

        return Schema(name=name, fields=schema_fields)

    def validate(
        self,
        data: Dict[str, Any],
        schema: Schema
    ) -> Tuple[bool, List[str]]:
        """Validate data against schema."""
        return self._schema_mapper.validate(data, schema)

    # ----- Quick Transforms -----

    def map_data(
        self,
        data: List[Any],
        function: Callable
    ) -> List[Any]:
        """Quick map transformation."""
        return MapTransformer(function).transform(data)

    def filter_data(
        self,
        data: List[Any],
        predicate: Callable
    ) -> List[Any]:
        """Quick filter transformation."""
        return FilterTransformer(predicate).transform(data)

    def reduce_data(
        self,
        data: List[Any],
        function: Callable,
        initial: Any = None
    ) -> Any:
        """Quick reduce transformation."""
        return ReduceTransformer(function, initial).transform(data)

    def group_data(
        self,
        data: List[Any],
        key_func: Callable
    ) -> Dict[Any, List[Any]]:
        """Quick group transformation."""
        return GroupTransformer(key_func).transform(data)

    def sort_data(
        self,
        data: List[Any],
        key_func: Optional[Callable] = None,
        reverse: bool = False
    ) -> List[Any]:
        """Quick sort transformation."""
        return SortTransformer(key_func, reverse).transform(data)

    def flatten_data(
        self,
        data: List[Any],
        depth: int = 1
    ) -> List[Any]:
        """Quick flatten transformation."""
        return FlattenTransformer(depth).transform(data)

    def aggregate_data(
        self,
        data: List[Any],
        aggregation: AggregationType,
        field: Optional[str] = None
    ) -> Any:
        """Quick aggregate transformation."""
        return AggregateTransformer(aggregation, field).transform(data)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "pipelines": self._pipeline_builder.count(),
            "batch_size": self._config.batch_size,
            "stream_mode": self._config.stream_mode.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Transformation Engine."""
    print("=" * 70)
    print("BAEL - TRANSFORMATION ENGINE DEMO")
    print("Data Transformation and Processing Pipelines")
    print("=" * 70)
    print()

    engine = TransformationEngine()

    # Sample data
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
        {"name": "Charlie", "age": 35, "city": "NYC"},
        {"name": "Diana", "age": 28, "city": "LA"},
        {"name": "Eve", "age": 32, "city": "Chicago"}
    ]

    # 1. Map Transformation
    print("1. MAP TRANSFORMATION:")
    print("-" * 40)

    names = engine.map_data(data, lambda x: x["name"])
    print(f"   Names: {names}")
    print()

    # 2. Filter Transformation
    print("2. FILTER TRANSFORMATION:")
    print("-" * 40)

    adults = engine.filter_data(data, lambda x: x["age"] >= 30)
    print(f"   Age >= 30: {[p['name'] for p in adults]}")
    print()

    # 3. Reduce Transformation
    print("3. REDUCE TRANSFORMATION:")
    print("-" * 40)

    total_age = engine.reduce_data(
        [p["age"] for p in data],
        lambda a, b: a + b,
        0
    )
    print(f"   Total age: {total_age}")
    print()

    # 4. Group Transformation
    print("4. GROUP TRANSFORMATION:")
    print("-" * 40)

    by_city = engine.group_data(data, lambda x: x["city"])

    for city, people in by_city.items():
        print(f"   {city}: {[p['name'] for p in people]}")
    print()

    # 5. Sort Transformation
    print("5. SORT TRANSFORMATION:")
    print("-" * 40)

    sorted_by_age = engine.sort_data(data, lambda x: x["age"])
    print(f"   By age: {[f'{p[\"name\"]}({p[\"age\"]})' for p in sorted_by_age]}")
    print()

    # 6. Flatten Transformation
    print("6. FLATTEN TRANSFORMATION:")
    print("-" * 40)

    nested = [[1, 2], [3, [4, 5]], [6]]
    flattened = engine.flatten_data(nested, depth=2)
    print(f"   Original: {nested}")
    print(f"   Flattened: {flattened}")
    print()

    # 7. Aggregate Transformation
    print("7. AGGREGATE TRANSFORMATION:")
    print("-" * 40)

    avg_age = engine.aggregate_data(data, AggregationType.AVG, "age")
    max_age = engine.aggregate_data(data, AggregationType.MAX, "age")
    count = engine.aggregate_data(data, AggregationType.COUNT, "age")

    print(f"   Average age: {avg_age:.1f}")
    print(f"   Max age: {max_age}")
    print(f"   Count: {count}")
    print()

    # 8. Create Pipeline
    print("8. CREATE PIPELINE:")
    print("-" * 40)

    pipeline = engine.create_pipeline("data_processor")
    engine.add_filter(pipeline.pipeline_id, "adults", lambda x: x["age"] >= 25)
    engine.add_map(pipeline.pipeline_id, "extract_names", lambda x: x["name"].upper())
    engine.add_sort(pipeline.pipeline_id, "alphabetical", None)

    print(f"   Pipeline: {pipeline.name}")
    print(f"   Transforms: {len(pipeline.transforms)}")
    print()

    # 9. Execute Pipeline
    print("9. EXECUTE PIPELINE:")
    print("-" * 40)

    result = engine.execute(pipeline.pipeline_id, data)

    print(f"   Success: {result.success}")
    print(f"   Records in: {result.records_in}")
    print(f"   Records out: {result.records_out}")
    print(f"   Result: {result.data}")
    print(f"   Duration: {result.duration:.4f}s")
    print()

    # 10. JSON Conversion
    print("10. JSON CONVERSION:")
    print("-" * 40)

    json_str = engine.to_json(data[:2])
    print(f"   JSON: {json_str[:60]}...")

    parsed = engine.from_json(json_str)
    print(f"   Parsed: {len(parsed)} records")
    print()

    # 11. CSV Conversion
    print("11. CSV CONVERSION:")
    print("-" * 40)

    csv_str = engine.to_csv(data[:2])
    print(f"   CSV:\n{csv_str}")

    parsed_csv = engine.from_csv(csv_str)
    print(f"   Parsed: {len(parsed_csv)} records")
    print()

    # 12. Schema Mapping
    print("12. SCHEMA MAPPING:")
    print("-" * 40)

    engine.add_mapping("user_format", {
        "user_name": "name",
        "user_age": "age",
        "location": "city"
    })

    mapped = engine.map_schema(data[0], "user_format")
    print(f"   Original: {data[0]}")
    print(f"   Mapped: {mapped}")
    print()

    # 13. Schema Validation
    print("13. SCHEMA VALIDATION:")
    print("-" * 40)

    schema = engine.create_schema("person", [
        ("name", SchemaType.STRING, True, None),
        ("age", SchemaType.INTEGER, True, None),
        ("city", SchemaType.STRING, False, "Unknown")
    ])

    valid, errors = engine.validate(data[0], schema)
    print(f"   Valid: {valid}")
    print(f"   Errors: {errors}")

    invalid_data = {"name": 123, "age": "old"}
    valid2, errors2 = engine.validate(invalid_data, schema)
    print(f"   Invalid data valid: {valid2}")
    print(f"   Errors: {errors2}")
    print()

    # 14. Chained Pipeline
    print("14. CHAINED PIPELINE:")
    print("-" * 40)

    numbers = list(range(1, 21))

    chain = engine.create_pipeline("number_chain")
    engine.add_filter(chain.pipeline_id, "even", lambda x: x % 2 == 0)
    engine.add_map(chain.pipeline_id, "square", lambda x: x ** 2)
    engine.add_sort(chain.pipeline_id, "desc", None, reverse=True)

    result = engine.execute(chain.pipeline_id, numbers)

    print(f"   Input: {numbers[:5]}... (20 numbers)")
    print(f"   Output: {result.data}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Transformation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
