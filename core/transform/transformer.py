#!/usr/bin/env python3
"""
BAEL - Data Transformer
Comprehensive data transformation and pipeline system.

This module provides powerful data transformation
capabilities with chainable operations.

Features:
- Chainable transformations
- Schema mapping
- Data validation
- Type coercion
- Aggregations
- Filtering
- Sorting
- Grouping
- Pivoting
- Custom transformers
"""

import asyncio
import copy
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
from functools import reduce
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Sequence, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class DataType(Enum):
    """Data type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    LIST = "list"
    DICT = "dict"
    NULL = "null"
    ANY = "any"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    LIST = "list"
    SET = "set"


class TransformAction(Enum):
    """Transform action types."""
    MAP = "map"
    FILTER = "filter"
    REDUCE = "reduce"
    SORT = "sort"
    GROUP = "group"
    FLATTEN = "flatten"
    UNIQUE = "unique"
    LIMIT = "limit"
    SKIP = "skip"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FieldMapping:
    """Field mapping configuration."""
    source: str
    target: str
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None
    required: bool = False


@dataclass
class SchemaField:
    """Schema field definition."""
    name: str
    data_type: DataType
    required: bool = False
    default: Any = None
    validators: List[Callable[[Any], bool]] = field(default_factory=list)


@dataclass
class TransformResult:
    """Transformation result."""
    success: bool
    data: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformStats:
    """Transformation statistics."""
    input_count: int = 0
    output_count: int = 0
    error_count: int = 0
    duration: float = 0.0
    transformations_applied: int = 0


# =============================================================================
# TYPE COERCION
# =============================================================================

class TypeCoercer:
    """Type coercion utilities."""

    @staticmethod
    def to_string(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def to_integer(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0
            # Handle comma-separated numbers
            value = value.replace(",", "")
            return int(float(value))
        return int(value)

    @staticmethod
    def to_float(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, float):
            return value
        if isinstance(value, (int, Decimal)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
            value = value.replace(",", "")
            return float(value)
        return float(value)

    @staticmethod
    def to_boolean(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)

    @staticmethod
    def to_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def to_list(value: Any) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set, frozenset)):
            return list(value)
        if isinstance(value, str):
            # Try JSON parse
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Split by comma
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value]

    @staticmethod
    def to_dict(value: Any) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        if hasattr(value, '__dict__'):
            return value.__dict__
        return {"value": value}

    @classmethod
    def coerce(cls, value: Any, target_type: DataType) -> Any:
        """Coerce value to target type."""
        converters = {
            DataType.STRING: cls.to_string,
            DataType.INTEGER: cls.to_integer,
            DataType.FLOAT: cls.to_float,
            DataType.BOOLEAN: cls.to_boolean,
            DataType.DATETIME: cls.to_datetime,
            DataType.DATE: lambda v: cls.to_datetime(v).date() if cls.to_datetime(v) else None,
            DataType.LIST: cls.to_list,
            DataType.DICT: cls.to_dict,
            DataType.NULL: lambda v: None,
            DataType.ANY: lambda v: v,
        }

        converter = converters.get(target_type)
        if converter:
            try:
                return converter(value)
            except Exception:
                return None
        return value


# =============================================================================
# TRANSFORMER BASE
# =============================================================================

class Transformer(ABC, Generic[T, R]):
    """Abstract base transformer."""

    @abstractmethod
    def transform(self, data: T) -> R:
        pass

    def __call__(self, data: T) -> R:
        return self.transform(data)


class FunctionTransformer(Transformer[T, R]):
    """Function-based transformer."""

    def __init__(self, func: Callable[[T], R]):
        self.func = func

    def transform(self, data: T) -> R:
        return self.func(data)


# =============================================================================
# RECORD TRANSFORMERS
# =============================================================================

class RecordTransformer:
    """Transform individual records (dictionaries)."""

    def __init__(self):
        self.mappings: List[FieldMapping] = []
        self.computed_fields: Dict[str, Callable[[Dict], Any]] = {}
        self.field_transforms: Dict[str, Callable[[Any], Any]] = {}
        self.field_renames: Dict[str, str] = {}
        self.include_fields: Optional[Set[str]] = None
        self.exclude_fields: Set[str] = set()

    def map_field(
        self,
        source: str,
        target: str = None,
        transform: Callable[[Any], Any] = None,
        default: Any = None,
        required: bool = False
    ) -> 'RecordTransformer':
        """Add field mapping."""
        self.mappings.append(FieldMapping(
            source=source,
            target=target or source,
            transform=transform,
            default=default,
            required=required
        ))
        return self

    def rename(self, old_name: str, new_name: str) -> 'RecordTransformer':
        """Rename a field."""
        self.field_renames[old_name] = new_name
        return self

    def add_computed(
        self,
        field_name: str,
        compute: Callable[[Dict], Any]
    ) -> 'RecordTransformer':
        """Add computed field."""
        self.computed_fields[field_name] = compute
        return self

    def add_transform(
        self,
        field_name: str,
        transform: Callable[[Any], Any]
    ) -> 'RecordTransformer':
        """Add field transform."""
        self.field_transforms[field_name] = transform
        return self

    def include(self, *fields: str) -> 'RecordTransformer':
        """Include only specified fields."""
        self.include_fields = set(fields)
        return self

    def exclude(self, *fields: str) -> 'RecordTransformer':
        """Exclude specified fields."""
        self.exclude_fields.update(fields)
        return self

    def transform(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a record."""
        result = {}

        # Apply mappings if defined
        if self.mappings:
            for mapping in self.mappings:
                value = self._get_nested(record, mapping.source)

                if value is None:
                    if mapping.required:
                        raise ValueError(f"Required field missing: {mapping.source}")
                    value = mapping.default

                if mapping.transform and value is not None:
                    value = mapping.transform(value)

                self._set_nested(result, mapping.target, value)
        else:
            # Copy all fields
            result = copy.deepcopy(record)

        # Apply field renames
        for old_name, new_name in self.field_renames.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)

        # Apply field transforms
        for field_name, transform in self.field_transforms.items():
            if field_name in result:
                result[field_name] = transform(result[field_name])

        # Add computed fields
        for field_name, compute in self.computed_fields.items():
            result[field_name] = compute(record)

        # Apply include/exclude
        if self.include_fields:
            result = {k: v for k, v in result.items() if k in self.include_fields}

        if self.exclude_fields:
            result = {k: v for k, v in result.items() if k not in self.exclude_fields}

        return result

    def _get_nested(self, data: Dict, path: str) -> Any:
        """Get nested value by dot-notation path."""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if 0 <= idx < len(value) else None
            else:
                return None

        return value

    def _set_nested(self, data: Dict, path: str, value: Any) -> None:
        """Set nested value by dot-notation path."""
        keys = path.split(".")

        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]

        data[keys[-1]] = value


# =============================================================================
# COLLECTION TRANSFORMERS
# =============================================================================

class CollectionTransformer:
    """Transform collections of records."""

    def __init__(self, data: List[Dict[str, Any]] = None):
        self.data = data or []
        self._operations: List[Tuple[str, Any]] = []

    def from_data(self, data: List[Dict[str, Any]]) -> 'CollectionTransformer':
        """Set source data."""
        self.data = data
        return self

    def map(
        self,
        func: Callable[[Dict], Dict]
    ) -> 'CollectionTransformer':
        """Map each record."""
        self._operations.append(("map", func))
        return self

    def filter(
        self,
        predicate: Callable[[Dict], bool]
    ) -> 'CollectionTransformer':
        """Filter records."""
        self._operations.append(("filter", predicate))
        return self

    def where(
        self,
        field: str,
        op: str,
        value: Any
    ) -> 'CollectionTransformer':
        """Filter by field condition."""
        ops = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a > b,
            "gte": lambda a, b: a >= b,
            "lt": lambda a, b: a < b,
            "lte": lambda a, b: a <= b,
            "in": lambda a, b: a in b,
            "nin": lambda a, b: a not in b,
            "contains": lambda a, b: b in a if isinstance(a, (str, list)) else False,
            "startswith": lambda a, b: a.startswith(b) if isinstance(a, str) else False,
            "endswith": lambda a, b: a.endswith(b) if isinstance(a, str) else False,
            "matches": lambda a, b: bool(re.match(b, a)) if isinstance(a, str) else False,
        }

        compare = ops.get(op)
        if not compare:
            raise ValueError(f"Unknown operator: {op}")

        def predicate(record: Dict) -> bool:
            field_value = record.get(field)
            try:
                return compare(field_value, value)
            except Exception:
                return False

        return self.filter(predicate)

    def sort(
        self,
        key: Union[str, Callable[[Dict], Any]],
        reverse: bool = False
    ) -> 'CollectionTransformer':
        """Sort records."""
        if isinstance(key, str):
            field = key
            key = lambda r: r.get(field)

        self._operations.append(("sort", (key, reverse)))
        return self

    def limit(self, n: int) -> 'CollectionTransformer':
        """Limit number of records."""
        self._operations.append(("limit", n))
        return self

    def skip(self, n: int) -> 'CollectionTransformer':
        """Skip n records."""
        self._operations.append(("skip", n))
        return self

    def unique(
        self,
        key: Union[str, Callable[[Dict], Any]] = None
    ) -> 'CollectionTransformer':
        """Keep unique records."""
        self._operations.append(("unique", key))
        return self

    def flatten(self, field: str) -> 'CollectionTransformer':
        """Flatten nested array field."""
        self._operations.append(("flatten", field))
        return self

    def group_by(
        self,
        key: Union[str, Callable[[Dict], Any]],
        aggregations: Dict[str, Tuple[str, AggregationType]] = None
    ) -> 'CollectionTransformer':
        """Group records by key with aggregations."""
        self._operations.append(("group", (key, aggregations)))
        return self

    def pivot(
        self,
        index: str,
        columns: str,
        values: str,
        agg: AggregationType = AggregationType.FIRST
    ) -> 'CollectionTransformer':
        """Pivot data."""
        self._operations.append(("pivot", (index, columns, values, agg)))
        return self

    def join(
        self,
        other: List[Dict],
        on: str,
        how: str = "inner"
    ) -> 'CollectionTransformer':
        """Join with another collection."""
        self._operations.append(("join", (other, on, how)))
        return self

    def transform_field(
        self,
        field: str,
        transform: Callable[[Any], Any]
    ) -> 'CollectionTransformer':
        """Transform a specific field."""
        def mapper(record: Dict) -> Dict:
            result = record.copy()
            if field in result:
                result[field] = transform(result[field])
            return result

        return self.map(mapper)

    def rename_field(
        self,
        old_name: str,
        new_name: str
    ) -> 'CollectionTransformer':
        """Rename a field."""
        def mapper(record: Dict) -> Dict:
            result = record.copy()
            if old_name in result:
                result[new_name] = result.pop(old_name)
            return result

        return self.map(mapper)

    def add_field(
        self,
        field: str,
        value: Union[Any, Callable[[Dict], Any]]
    ) -> 'CollectionTransformer':
        """Add a field."""
        def mapper(record: Dict) -> Dict:
            result = record.copy()
            if callable(value):
                result[field] = value(record)
            else:
                result[field] = value
            return result

        return self.map(mapper)

    def remove_field(self, *fields: str) -> 'CollectionTransformer':
        """Remove fields."""
        def mapper(record: Dict) -> Dict:
            return {k: v for k, v in record.items() if k not in fields}

        return self.map(mapper)

    def execute(self) -> List[Dict[str, Any]]:
        """Execute all operations and return result."""
        result = list(self.data)

        for op_name, op_data in self._operations:
            if op_name == "map":
                result = [op_data(r) for r in result]

            elif op_name == "filter":
                result = [r for r in result if op_data(r)]

            elif op_name == "sort":
                key, reverse = op_data
                result = sorted(result, key=key, reverse=reverse)

            elif op_name == "limit":
                result = result[:op_data]

            elif op_name == "skip":
                result = result[op_data:]

            elif op_name == "unique":
                key = op_data
                seen = set()
                unique_result = []
                for r in result:
                    k = key(r) if callable(key) else r.get(key) if key else json.dumps(r, sort_keys=True)
                    if k not in seen:
                        seen.add(k)
                        unique_result.append(r)
                result = unique_result

            elif op_name == "flatten":
                field = op_data
                flat_result = []
                for r in result:
                    values = r.get(field, [])
                    if isinstance(values, list):
                        for v in values:
                            new_record = r.copy()
                            new_record[field] = v
                            flat_result.append(new_record)
                    else:
                        flat_result.append(r)
                result = flat_result

            elif op_name == "group":
                key, aggregations = op_data
                result = self._execute_group(result, key, aggregations)

            elif op_name == "pivot":
                index, columns, values, agg = op_data
                result = self._execute_pivot(result, index, columns, values, agg)

            elif op_name == "join":
                other, on, how = op_data
                result = self._execute_join(result, other, on, how)

        return result

    def _execute_group(
        self,
        data: List[Dict],
        key: Union[str, Callable],
        aggregations: Dict[str, Tuple[str, AggregationType]] = None
    ) -> List[Dict]:
        """Execute group by operation."""
        groups = defaultdict(list)

        for record in data:
            if callable(key):
                k = key(record)
            else:
                k = record.get(key)
            groups[k].append(record)

        result = []

        for group_key, records in groups.items():
            row = {"_key": group_key, "_count": len(records)}

            if aggregations:
                for agg_name, (field, agg_type) in aggregations.items():
                    values = [r.get(field) for r in records if r.get(field) is not None]
                    row[agg_name] = self._aggregate(values, agg_type)

            result.append(row)

        return result

    def _aggregate(
        self,
        values: List[Any],
        agg_type: AggregationType
    ) -> Any:
        """Apply aggregation."""
        if not values:
            return None

        if agg_type == AggregationType.SUM:
            return sum(values)
        elif agg_type == AggregationType.AVG:
            return sum(values) / len(values)
        elif agg_type == AggregationType.MIN:
            return min(values)
        elif agg_type == AggregationType.MAX:
            return max(values)
        elif agg_type == AggregationType.COUNT:
            return len(values)
        elif agg_type == AggregationType.FIRST:
            return values[0]
        elif agg_type == AggregationType.LAST:
            return values[-1]
        elif agg_type == AggregationType.LIST:
            return values
        elif agg_type == AggregationType.SET:
            return list(set(values))

        return None

    def _execute_pivot(
        self,
        data: List[Dict],
        index: str,
        columns: str,
        values: str,
        agg: AggregationType
    ) -> List[Dict]:
        """Execute pivot operation."""
        # Group by index and column
        groups = defaultdict(lambda: defaultdict(list))
        all_columns = set()

        for record in data:
            idx = record.get(index)
            col = record.get(columns)
            val = record.get(values)

            if idx is not None and col is not None:
                groups[idx][col].append(val)
                all_columns.add(col)

        # Build result
        result = []

        for idx, cols in groups.items():
            row = {index: idx}
            for col in all_columns:
                col_values = cols.get(col, [])
                row[col] = self._aggregate(col_values, agg)
            result.append(row)

        return result

    def _execute_join(
        self,
        left: List[Dict],
        right: List[Dict],
        on: str,
        how: str
    ) -> List[Dict]:
        """Execute join operation."""
        # Index right side
        right_index = defaultdict(list)
        for r in right:
            key = r.get(on)
            if key is not None:
                right_index[key].append(r)

        result = []
        right_keys_used = set()

        for left_record in left:
            left_key = left_record.get(on)
            matches = right_index.get(left_key, [])

            if matches:
                for right_record in matches:
                    merged = {**left_record, **right_record}
                    result.append(merged)
                    right_keys_used.add(left_key)
            elif how in ("left", "outer"):
                result.append(left_record.copy())

        # Add unmatched right records for right/outer join
        if how in ("right", "outer"):
            for r in right:
                key = r.get(on)
                if key not in right_keys_used:
                    result.append(r.copy())

        return result

    # Aggregation shortcuts
    def count(self) -> int:
        return len(self.execute())

    def sum(self, field: str) -> float:
        data = self.execute()
        return sum(r.get(field, 0) for r in data)

    def avg(self, field: str) -> float:
        data = self.execute()
        values = [r.get(field) for r in data if r.get(field) is not None]
        return sum(values) / len(values) if values else 0

    def min_value(self, field: str) -> Any:
        data = self.execute()
        values = [r.get(field) for r in data if r.get(field) is not None]
        return min(values) if values else None

    def max_value(self, field: str) -> Any:
        data = self.execute()
        values = [r.get(field) for r in data if r.get(field) is not None]
        return max(values) if values else None


# =============================================================================
# DATA PIPELINE
# =============================================================================

class PipelineStep(ABC):
    """Abstract pipeline step."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def process(self, data: Any) -> Any:
        pass


class TransformStep(PipelineStep):
    """Transformation step."""

    def __init__(
        self,
        name: str,
        func: Callable[[Any], Any]
    ):
        self._name = name
        self.func = func

    @property
    def name(self) -> str:
        return self._name

    async def process(self, data: Any) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(data)
        return self.func(data)


class ValidateStep(PipelineStep):
    """Validation step."""

    def __init__(
        self,
        name: str,
        validator: Callable[[Any], bool],
        error_message: str = "Validation failed"
    ):
        self._name = name
        self.validator = validator
        self.error_message = error_message

    @property
    def name(self) -> str:
        return self._name

    async def process(self, data: Any) -> Any:
        if not self.validator(data):
            raise ValueError(self.error_message)
        return data


class DataPipeline:
    """
    Data transformation pipeline.
    """

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.steps: List[PipelineStep] = []
        self.error_handler: Optional[Callable[[Exception, Any], Any]] = None

    def add_step(self, step: PipelineStep) -> 'DataPipeline':
        """Add a step."""
        self.steps.append(step)
        return self

    def transform(
        self,
        name: str,
        func: Callable[[Any], Any]
    ) -> 'DataPipeline':
        """Add transform step."""
        return self.add_step(TransformStep(name, func))

    def validate(
        self,
        name: str,
        validator: Callable[[Any], bool],
        error_message: str = "Validation failed"
    ) -> 'DataPipeline':
        """Add validation step."""
        return self.add_step(ValidateStep(name, validator, error_message))

    def on_error(
        self,
        handler: Callable[[Exception, Any], Any]
    ) -> 'DataPipeline':
        """Set error handler."""
        self.error_handler = handler
        return self

    async def execute(self, data: Any) -> TransformResult:
        """Execute the pipeline."""
        start_time = time.time()
        current_data = data
        errors = []
        warnings = []
        steps_completed = 0

        for step in self.steps:
            try:
                current_data = await step.process(current_data)
                steps_completed += 1
            except Exception as e:
                error_msg = f"Step '{step.name}' failed: {str(e)}"
                errors.append(error_msg)

                if self.error_handler:
                    try:
                        current_data = self.error_handler(e, current_data)
                    except Exception:
                        break
                else:
                    break

        duration = time.time() - start_time

        return TransformResult(
            success=len(errors) == 0,
            data=current_data,
            errors=errors,
            warnings=warnings,
            metadata={
                "duration": duration,
                "steps_total": len(self.steps),
                "steps_completed": steps_completed
            }
        )

    def execute_sync(self, data: Any) -> TransformResult:
        """Execute synchronously."""
        return asyncio.run(self.execute(data))


# =============================================================================
# TRANSFORMER MANAGER
# =============================================================================

class TransformerManager:
    """
    Master data transformer manager for BAEL.
    """

    def __init__(self):
        self.coercer = TypeCoercer()
        self.pipelines: Dict[str, DataPipeline] = {}

        # Statistics
        self.stats = {
            "records_transformed": 0,
            "pipelines_executed": 0,
            "errors": 0
        }

    def collection(
        self,
        data: List[Dict[str, Any]] = None
    ) -> CollectionTransformer:
        """Create collection transformer."""
        return CollectionTransformer(data)

    def record(self) -> RecordTransformer:
        """Create record transformer."""
        return RecordTransformer()

    def pipeline(self, name: str = "pipeline") -> DataPipeline:
        """Create data pipeline."""
        pipeline = DataPipeline(name)
        self.pipelines[name] = pipeline
        return pipeline

    def coerce(self, value: Any, target_type: DataType) -> Any:
        """Coerce value to type."""
        return self.coercer.coerce(value, target_type)

    async def transform_records(
        self,
        data: List[Dict[str, Any]],
        transformer: RecordTransformer
    ) -> List[Dict[str, Any]]:
        """Transform records."""
        result = []

        for record in data:
            try:
                transformed = transformer.transform(record)
                result.append(transformed)
                self.stats["records_transformed"] += 1
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Transform error: {e}")

        return result

    async def run_pipeline(
        self,
        pipeline_name: str,
        data: Any
    ) -> TransformResult:
        """Run named pipeline."""
        pipeline = self.pipelines.get(pipeline_name)

        if not pipeline:
            return TransformResult(
                success=False,
                data=None,
                errors=[f"Pipeline not found: {pipeline_name}"]
            )

        result = await pipeline.execute(data)
        self.stats["pipelines_executed"] += 1

        if not result.success:
            self.stats["errors"] += len(result.errors)

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.stats.copy()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Transformer."""
    print("=" * 70)
    print("BAEL - DATA TRANSFORMER DEMO")
    print("Comprehensive Data Transformation System")
    print("=" * 70)
    print()

    manager = TransformerManager()

    # Sample data
    users = [
        {"id": 1, "name": "Alice", "age": 30, "dept": "Engineering", "salary": 75000},
        {"id": 2, "name": "Bob", "age": 25, "dept": "Marketing", "salary": 55000},
        {"id": 3, "name": "Charlie", "age": 35, "dept": "Engineering", "salary": 85000},
        {"id": 4, "name": "Diana", "age": 28, "dept": "Marketing", "salary": 60000},
        {"id": 5, "name": "Eve", "age": 32, "dept": "Engineering", "salary": 80000},
    ]

    # 1. Type Coercion
    print("1. TYPE COERCION:")
    print("-" * 40)

    print(f"   '123' -> int: {manager.coerce('123', DataType.INTEGER)}")
    print(f"   '45.67' -> float: {manager.coerce('45.67', DataType.FLOAT)}")
    print(f"   'yes' -> bool: {manager.coerce('yes', DataType.BOOLEAN)}")
    print(f"   1609459200 -> datetime: {manager.coerce(1609459200, DataType.DATETIME)}")
    print(f"   'a,b,c' -> list: {manager.coerce('a,b,c', DataType.LIST)}")
    print()

    # 2. Record Transformer
    print("2. RECORD TRANSFORMER:")
    print("-" * 40)

    transformer = manager.record()
    transformer.map_field("name", "full_name", transform=str.upper)
    transformer.map_field("age", "age_group", transform=lambda a: "Senior" if a >= 30 else "Junior")
    transformer.add_computed("annual_bonus", lambda r: r.get("salary", 0) * 0.1)
    transformer.exclude("dept")

    sample = users[0]
    transformed = transformer.transform(sample)
    print(f"   Original: {sample}")
    print(f"   Transformed: {transformed}")
    print()

    # 3. Collection Filtering
    print("3. COLLECTION FILTERING:")
    print("-" * 40)

    result = (
        manager.collection(users)
        .where("age", "gte", 30)
        .execute()
    )

    print(f"   Users age >= 30: {len(result)}")
    for r in result:
        print(f"     {r['name']} (age: {r['age']})")
    print()

    # 4. Sorting
    print("4. SORTING:")
    print("-" * 40)

    result = (
        manager.collection(users)
        .sort("salary", reverse=True)
        .limit(3)
        .execute()
    )

    print("   Top 3 by salary:")
    for r in result:
        print(f"     {r['name']}: ${r['salary']:,}")
    print()

    # 5. Aggregation
    print("5. AGGREGATION:")
    print("-" * 40)

    col = manager.collection(users)

    print(f"   Total records: {col.count()}")
    print(f"   Total salary: ${col.sum('salary'):,}")
    print(f"   Average age: {col.avg('age'):.1f}")
    print(f"   Max salary: ${col.max_value('salary'):,}")
    print()

    # 6. Group By
    print("6. GROUP BY:")
    print("-" * 40)

    result = (
        manager.collection(users)
        .group_by(
            "dept",
            {
                "avg_salary": ("salary", AggregationType.AVG),
                "count": ("id", AggregationType.COUNT),
                "max_age": ("age", AggregationType.MAX)
            }
        )
        .execute()
    )

    for group in result:
        print(f"   {group['_key']}:")
        print(f"     Count: {group['count']}")
        print(f"     Avg Salary: ${group['avg_salary']:,.0f}")
        print(f"     Max Age: {group['max_age']}")
    print()

    # 7. Chained Operations
    print("7. CHAINED OPERATIONS:")
    print("-" * 40)

    result = (
        manager.collection(users)
        .where("dept", "eq", "Engineering")
        .add_field("level", lambda r: "Senior" if r["age"] > 30 else "Junior")
        .sort("salary", reverse=True)
        .remove_field("dept")
        .execute()
    )

    print("   Engineering team by salary:")
    for r in result:
        print(f"     {r['name']} ({r['level']}): ${r['salary']:,}")
    print()

    # 8. Data Pipeline
    print("8. DATA PIPELINE:")
    print("-" * 40)

    pipeline = (
        manager.pipeline("user_processing")
        .transform("normalize", lambda data: [
            {**r, "name": r["name"].strip().title()} for r in data
        ])
        .validate("has_data", lambda data: len(data) > 0, "No data provided")
        .transform("add_status", lambda data: [
            {**r, "status": "active"} for r in data
        ])
        .transform("calculate_tax", lambda data: [
            {**r, "tax": r["salary"] * 0.25} for r in data
        ])
    )

    result = await pipeline.execute(users)

    print(f"   Pipeline success: {result.success}")
    print(f"   Steps completed: {result.metadata['steps_completed']}")
    print(f"   Duration: {result.metadata['duration']*1000:.2f}ms")
    print(f"   Sample result: {result.data[0]}")
    print()

    # 9. Join Operations
    print("9. JOIN OPERATIONS:")
    print("-" * 40)

    departments = [
        {"dept": "Engineering", "budget": 500000, "location": "Building A"},
        {"dept": "Marketing", "budget": 200000, "location": "Building B"},
        {"dept": "HR", "budget": 100000, "location": "Building C"},
    ]

    result = (
        manager.collection(users)
        .join(departments, "dept", "left")
        .execute()
    )

    print("   Users with department info:")
    for r in result[:3]:
        print(f"     {r['name']} - {r['dept']} ({r.get('location', 'N/A')})")
    print()

    # 10. Unique and Flatten
    print("10. UNIQUE AND FLATTEN:")
    print("-" * 40)

    data_with_tags = [
        {"id": 1, "tags": ["python", "ml"]},
        {"id": 2, "tags": ["javascript", "web"]},
        {"id": 3, "tags": ["python", "data"]},
    ]

    result = (
        manager.collection(data_with_tags)
        .flatten("tags")
        .execute()
    )

    print(f"   Flattened tags ({len(result)} records):")
    for r in result:
        print(f"     ID {r['id']}: {r['tags']}")

    unique_tags = (
        manager.collection(result)
        .unique("tags")
        .execute()
    )

    print(f"   Unique tags: {[r['tags'] for r in unique_tags]}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Records transformed: {stats['records_transformed']}")
    print(f"    Pipelines executed: {stats['pipelines_executed']}")
    print(f"    Errors: {stats['errors']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Transformer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
