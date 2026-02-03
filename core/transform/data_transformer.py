#!/usr/bin/env python3
"""
BAEL - Data Transformer
Advanced data transformation engine for AI agent operations.

Features:
- Pipeline transformations
- Type conversions
- Data mapping
- Schema transformations
- Validation integration
- Reversible transforms
- Streaming transforms
- Batch processing
- Custom transformers
- Transform chains
"""

import asyncio
import copy
import functools
import hashlib
import json
import re
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class TransformDirection(Enum):
    """Transformation direction."""
    FORWARD = "forward"
    REVERSE = "reverse"


class TransformStrategy(Enum):
    """Transformation strategy."""
    STRICT = "strict"
    LENIENT = "lenient"
    SKIP_ERRORS = "skip_errors"


class DataType(Enum):
    """Supported data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    NULL = "null"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TransformResult:
    """Result of a transformation."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class TransformContext:
    """Context for transformations."""
    source_type: Optional[DataType] = None
    target_type: Optional[DataType] = None
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    source: str
    target: str
    transformer: Optional[str] = None
    default: Any = None
    required: bool = False


@dataclass
class SchemaDefinition:
    """Schema definition."""
    fields: Dict[str, DataType] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformStats:
    """Transformation statistics."""
    total_transforms: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0


# =============================================================================
# TRANSFORMER BASE
# =============================================================================

class Transformer(ABC, Generic[S, R]):
    """
    Abstract base transformer.
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def transform(self, data: S, ctx: Optional[TransformContext] = None) -> R:
        """Transform data forward."""
        pass

    def reverse(self, data: R, ctx: Optional[TransformContext] = None) -> S:
        """Transform data in reverse (optional)."""
        raise NotImplementedError("Reverse transform not supported")

    @property
    def reversible(self) -> bool:
        """Check if transformer is reversible."""
        return False


# =============================================================================
# TYPE TRANSFORMERS
# =============================================================================

class StringTransformer(Transformer[Any, str]):
    """Convert to string."""

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> str:
        if data is None:
            return ""
        return str(data)

    @property
    def reversible(self) -> bool:
        return False


class IntegerTransformer(Transformer[Any, int]):
    """Convert to integer."""

    def __init__(self, default: int = 0):
        self.default = default

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> int:
        if data is None:
            return self.default

        if isinstance(data, bool):
            return 1 if data else 0

        if isinstance(data, str):
            data = data.strip()
            if not data:
                return self.default
            # Handle floats in strings
            if '.' in data:
                return int(float(data))
            return int(data)

        return int(data)


class FloatTransformer(Transformer[Any, float]):
    """Convert to float."""

    def __init__(self, default: float = 0.0, precision: Optional[int] = None):
        self.default = default
        self.precision = precision

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> float:
        if data is None:
            return self.default

        if isinstance(data, str):
            data = data.strip()
            if not data:
                return self.default

        result = float(data)

        if self.precision is not None:
            result = round(result, self.precision)

        return result


class BooleanTransformer(Transformer[Any, bool]):
    """Convert to boolean."""

    TRUTHY = {'true', 'yes', '1', 'on', 't', 'y'}
    FALSY = {'false', 'no', '0', 'off', 'f', 'n', ''}

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> bool:
        if data is None:
            return False

        if isinstance(data, bool):
            return data

        if isinstance(data, str):
            lower = data.lower().strip()
            if lower in self.TRUTHY:
                return True
            if lower in self.FALSY:
                return False
            raise ValueError(f"Cannot convert '{data}' to boolean")

        return bool(data)


class DateTimeTransformer(Transformer[Any, datetime]):
    """Convert to datetime."""

    FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]

    def __init__(self, format: Optional[str] = None):
        self.format = format

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> datetime:
        if isinstance(data, datetime):
            return data

        if isinstance(data, (int, float)):
            return datetime.fromtimestamp(data)

        if isinstance(data, str):
            if self.format:
                return datetime.strptime(data, self.format)

            for fmt in self.FORMATS:
                try:
                    return datetime.strptime(data, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Cannot parse datetime: {data}")

        raise TypeError(f"Cannot convert {type(data)} to datetime")

    def reverse(self, data: datetime, ctx: Optional[TransformContext] = None) -> str:
        fmt = self.format or "%Y-%m-%dT%H:%M:%S"
        return data.strftime(fmt)

    @property
    def reversible(self) -> bool:
        return True


class ListTransformer(Transformer[Any, list]):
    """Convert to list."""

    def __init__(self, item_transformer: Optional[Transformer] = None):
        self.item_transformer = item_transformer

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> list:
        if data is None:
            return []

        if isinstance(data, str):
            if data.startswith('['):
                data = json.loads(data)
            else:
                data = [data]

        if not isinstance(data, (list, tuple)):
            data = [data]

        result = list(data)

        if self.item_transformer:
            result = [self.item_transformer.transform(item, ctx) for item in result]

        return result


class DictTransformer(Transformer[Any, dict]):
    """Convert to dictionary."""

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> dict:
        if data is None:
            return {}

        if isinstance(data, dict):
            return dict(data)

        if isinstance(data, str):
            return json.loads(data)

        if hasattr(data, '__dict__'):
            return dict(data.__dict__)

        raise TypeError(f"Cannot convert {type(data)} to dict")


# =============================================================================
# STRING TRANSFORMERS
# =============================================================================

class UpperTransformer(Transformer[str, str]):
    """Convert to uppercase."""

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        return str(data).upper()

    def reverse(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        return data.lower()

    @property
    def reversible(self) -> bool:
        return True


class LowerTransformer(Transformer[str, str]):
    """Convert to lowercase."""

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        return str(data).lower()


class TrimTransformer(Transformer[str, str]):
    """Trim whitespace."""

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        return str(data).strip()


class SlugTransformer(Transformer[str, str]):
    """Convert to URL slug."""

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        text = str(data).lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')


class MaskTransformer(Transformer[str, str]):
    """Mask sensitive data."""

    def __init__(self, visible_chars: int = 4, mask_char: str = '*'):
        self.visible_chars = visible_chars
        self.mask_char = mask_char

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        text = str(data)
        if len(text) <= self.visible_chars:
            return self.mask_char * len(text)

        visible = text[-self.visible_chars:]
        masked = self.mask_char * (len(text) - self.visible_chars)
        return masked + visible


class HashTransformer(Transformer[str, str]):
    """Hash data."""

    def __init__(self, algorithm: str = 'sha256'):
        self.algorithm = algorithm

    def transform(self, data: str, ctx: Optional[TransformContext] = None) -> str:
        h = hashlib.new(self.algorithm)
        h.update(str(data).encode())
        return h.hexdigest()


# =============================================================================
# COMPOSITE TRANSFORMERS
# =============================================================================

class ChainTransformer(Transformer[Any, Any]):
    """Chain multiple transformers."""

    def __init__(self, *transformers: Transformer):
        self.transformers = list(transformers)

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> Any:
        result = data
        for transformer in self.transformers:
            result = transformer.transform(result, ctx)
        return result

    def reverse(self, data: Any, ctx: Optional[TransformContext] = None) -> Any:
        result = data
        for transformer in reversed(self.transformers):
            if transformer.reversible:
                result = transformer.reverse(result, ctx)
            else:
                raise NotImplementedError(
                    f"{transformer.name} is not reversible"
                )
        return result

    @property
    def reversible(self) -> bool:
        return all(t.reversible for t in self.transformers)


class ConditionalTransformer(Transformer[Any, Any]):
    """Apply transformer conditionally."""

    def __init__(
        self,
        condition: Callable[[Any], bool],
        if_true: Transformer,
        if_false: Optional[Transformer] = None
    ):
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> Any:
        if self.condition(data):
            return self.if_true.transform(data, ctx)
        elif self.if_false:
            return self.if_false.transform(data, ctx)
        return data


class DefaultTransformer(Transformer[Any, Any]):
    """Apply default value if None."""

    def __init__(self, default: Any, inner: Optional[Transformer] = None):
        self.default = default
        self.inner = inner

    def transform(self, data: Any, ctx: Optional[TransformContext] = None) -> Any:
        if data is None:
            return self.default

        if self.inner:
            return self.inner.transform(data, ctx)
        return data


# =============================================================================
# DATA MAPPER
# =============================================================================

class DataMapper:
    """
    Maps data between different schemas.
    """

    def __init__(self, mappings: Optional[List[FieldMapping]] = None):
        self.mappings = mappings or []
        self._transformers: Dict[str, Transformer] = {}

    def add_mapping(self, mapping: FieldMapping) -> None:
        """Add a field mapping."""
        self.mappings.append(mapping)

    def register_transformer(self, name: str, transformer: Transformer) -> None:
        """Register a named transformer."""
        self._transformers[name] = transformer

    def map(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Map source data to target schema."""
        result = {}

        for mapping in self.mappings:
            value = self._get_nested(source, mapping.source)

            if value is None:
                if mapping.required:
                    raise ValueError(f"Required field missing: {mapping.source}")
                value = mapping.default

            if value is not None and mapping.transformer:
                transformer = self._transformers.get(mapping.transformer)
                if transformer:
                    value = transformer.transform(value)

            self._set_nested(result, mapping.target, value)

        return result

    def _get_nested(self, data: Dict, path: str) -> Any:
        """Get nested value."""
        parts = path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _set_nested(self, data: Dict, path: str, value: Any) -> None:
        """Set nested value."""
        parts = path.split('.')
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


# =============================================================================
# TRANSFORM PIPELINE
# =============================================================================

class TransformPipeline:
    """
    Pipeline of transformations.
    """

    def __init__(self, name: str = ""):
        self.name = name or str(uuid.uuid4())[:8]
        self._steps: List[Tuple[str, Transformer]] = []

    def add_step(self, name: str, transformer: Transformer) -> 'TransformPipeline':
        """Add a transformation step."""
        self._steps.append((name, transformer))
        return self

    def transform(
        self,
        data: Any,
        strategy: TransformStrategy = TransformStrategy.STRICT
    ) -> TransformResult:
        """Execute the pipeline."""
        start_time = time.time()
        current = data
        warnings = []

        for step_name, transformer in self._steps:
            try:
                current = transformer.transform(current)
            except Exception as e:
                if strategy == TransformStrategy.STRICT:
                    return TransformResult(
                        success=False,
                        error=f"Step '{step_name}' failed: {e}",
                        duration_ms=(time.time() - start_time) * 1000
                    )
                elif strategy == TransformStrategy.LENIENT:
                    warnings.append(f"Step '{step_name}': {e}")
                # SKIP_ERRORS: continue with current value

        return TransformResult(
            success=True,
            data=current,
            warnings=warnings,
            duration_ms=(time.time() - start_time) * 1000
        )

    def reverse(self, data: Any) -> TransformResult:
        """Reverse the pipeline."""
        start_time = time.time()
        current = data

        for step_name, transformer in reversed(self._steps):
            if not transformer.reversible:
                return TransformResult(
                    success=False,
                    error=f"Step '{step_name}' is not reversible",
                    duration_ms=(time.time() - start_time) * 1000
                )
            current = transformer.reverse(current)

        return TransformResult(
            success=True,
            data=current,
            duration_ms=(time.time() - start_time) * 1000
        )


# =============================================================================
# BATCH TRANSFORMER
# =============================================================================

class BatchTransformer:
    """
    Batch data transformer.
    """

    def __init__(
        self,
        transformer: Transformer,
        batch_size: int = 100,
        parallel: bool = False
    ):
        self.transformer = transformer
        self.batch_size = batch_size
        self.parallel = parallel

    def transform(
        self,
        items: List[Any],
        strategy: TransformStrategy = TransformStrategy.STRICT
    ) -> List[TransformResult]:
        """Transform items in batches."""
        results = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = self._process_batch(batch, strategy)
            results.extend(batch_results)

        return results

    def _process_batch(
        self,
        batch: List[Any],
        strategy: TransformStrategy
    ) -> List[TransformResult]:
        """Process a single batch."""
        results = []

        for item in batch:
            start = time.time()
            try:
                transformed = self.transformer.transform(item)
                results.append(TransformResult(
                    success=True,
                    data=transformed,
                    duration_ms=(time.time() - start) * 1000
                ))
            except Exception as e:
                if strategy == TransformStrategy.STRICT:
                    raise
                results.append(TransformResult(
                    success=False,
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000
                ))

        return results


# =============================================================================
# DATA TRANSFORMER MANAGER
# =============================================================================

class DataTransformer:
    """
    Data Transformer for BAEL.

    Central transformation management.
    """

    def __init__(self):
        self._transformers: Dict[str, Transformer] = {}
        self._pipelines: Dict[str, TransformPipeline] = {}
        self._mappers: Dict[str, DataMapper] = {}
        self._stats = TransformStats()
        self._lock = threading.RLock()

        # Register built-in transformers
        self._register_builtin()

    def _register_builtin(self) -> None:
        """Register built-in transformers."""
        self._transformers = {
            "string": StringTransformer(),
            "integer": IntegerTransformer(),
            "float": FloatTransformer(),
            "boolean": BooleanTransformer(),
            "datetime": DateTimeTransformer(),
            "list": ListTransformer(),
            "dict": DictTransformer(),
            "upper": UpperTransformer(),
            "lower": LowerTransformer(),
            "trim": TrimTransformer(),
            "slug": SlugTransformer(),
            "mask": MaskTransformer(),
            "hash": HashTransformer()
        }

    # -------------------------------------------------------------------------
    # REGISTRATION
    # -------------------------------------------------------------------------

    def register(self, name: str, transformer: Transformer) -> None:
        """Register a transformer."""
        with self._lock:
            self._transformers[name] = transformer

    def register_pipeline(self, name: str, pipeline: TransformPipeline) -> None:
        """Register a pipeline."""
        with self._lock:
            self._pipelines[name] = pipeline

    def register_mapper(self, name: str, mapper: DataMapper) -> None:
        """Register a data mapper."""
        with self._lock:
            self._mappers[name] = mapper

    # -------------------------------------------------------------------------
    # TRANSFORMATION
    # -------------------------------------------------------------------------

    def transform(
        self,
        data: Any,
        transformer_name: str,
        ctx: Optional[TransformContext] = None
    ) -> TransformResult:
        """Transform data using a named transformer."""
        start = time.time()

        with self._lock:
            transformer = self._transformers.get(transformer_name)

        if not transformer:
            return TransformResult(
                success=False,
                error=f"Transformer not found: {transformer_name}"
            )

        try:
            result = transformer.transform(data, ctx)

            with self._lock:
                self._stats.total_transforms += 1
                self._stats.successful += 1

            return TransformResult(
                success=True,
                data=result,
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            with self._lock:
                self._stats.total_transforms += 1
                self._stats.failed += 1

            return TransformResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def run_pipeline(
        self,
        data: Any,
        pipeline_name: str,
        strategy: TransformStrategy = TransformStrategy.STRICT
    ) -> TransformResult:
        """Run a named pipeline."""
        with self._lock:
            pipeline = self._pipelines.get(pipeline_name)

        if not pipeline:
            return TransformResult(
                success=False,
                error=f"Pipeline not found: {pipeline_name}"
            )

        return pipeline.transform(data, strategy)

    def map(self, data: Dict[str, Any], mapper_name: str) -> TransformResult:
        """Map data using a named mapper."""
        start = time.time()

        with self._lock:
            mapper = self._mappers.get(mapper_name)

        if not mapper:
            return TransformResult(
                success=False,
                error=f"Mapper not found: {mapper_name}"
            )

        try:
            result = mapper.map(data)
            return TransformResult(
                success=True,
                data=result,
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return TransformResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    def to_string(self, data: Any) -> str:
        return self._transformers["string"].transform(data)

    def to_int(self, data: Any) -> int:
        return self._transformers["integer"].transform(data)

    def to_float(self, data: Any) -> float:
        return self._transformers["float"].transform(data)

    def to_bool(self, data: Any) -> bool:
        return self._transformers["boolean"].transform(data)

    def to_datetime(self, data: Any) -> datetime:
        return self._transformers["datetime"].transform(data)

    def to_list(self, data: Any) -> list:
        return self._transformers["list"].transform(data)

    def to_dict(self, data: Any) -> dict:
        return self._transformers["dict"].transform(data)

    def to_upper(self, data: str) -> str:
        return self._transformers["upper"].transform(data)

    def to_lower(self, data: str) -> str:
        return self._transformers["lower"].transform(data)

    def to_slug(self, data: str) -> str:
        return self._transformers["slug"].transform(data)

    def mask(self, data: str) -> str:
        return self._transformers["mask"].transform(data)

    def hash(self, data: str) -> str:
        return self._transformers["hash"].transform(data)

    # -------------------------------------------------------------------------
    # BATCH
    # -------------------------------------------------------------------------

    def batch_transform(
        self,
        items: List[Any],
        transformer_name: str,
        batch_size: int = 100
    ) -> List[TransformResult]:
        """Transform items in batches."""
        with self._lock:
            transformer = self._transformers.get(transformer_name)

        if not transformer:
            return [TransformResult(
                success=False,
                error=f"Transformer not found: {transformer_name}"
            )]

        batch_transformer = BatchTransformer(transformer, batch_size)
        return batch_transformer.transform(items)

    # -------------------------------------------------------------------------
    # PIPELINE BUILDER
    # -------------------------------------------------------------------------

    def create_pipeline(self, name: str = "") -> TransformPipeline:
        """Create a new pipeline."""
        return TransformPipeline(name)

    def create_mapper(self) -> DataMapper:
        """Create a new data mapper."""
        return DataMapper()

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self) -> TransformStats:
        """Get transformation statistics."""
        with self._lock:
            n = self._stats.total_transforms
            return TransformStats(
                total_transforms=n,
                successful=self._stats.successful,
                failed=self._stats.failed,
                avg_duration_ms=self._stats.avg_duration_ms
            )

    def list_transformers(self) -> List[str]:
        """List registered transformers."""
        with self._lock:
            return list(self._transformers.keys())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Transformer."""
    print("=" * 70)
    print("BAEL - DATA TRANSFORMER DEMO")
    print("Advanced Data Transformation for AI Agents")
    print("=" * 70)
    print()

    transformer = DataTransformer()

    # 1. Basic Type Conversions
    print("1. BASIC TYPE CONVERSIONS:")
    print("-" * 40)

    print(f"   to_string(123): '{transformer.to_string(123)}'")
    print(f"   to_int('42'): {transformer.to_int('42')}")
    print(f"   to_float('3.14'): {transformer.to_float('3.14')}")
    print(f"   to_bool('yes'): {transformer.to_bool('yes')}")
    print(f"   to_list('item'): {transformer.to_list('item')}")
    print()

    # 2. String Transformations
    print("2. STRING TRANSFORMATIONS:")
    print("-" * 40)

    print(f"   to_upper('hello'): '{transformer.to_upper('hello')}'")
    print(f"   to_lower('WORLD'): '{transformer.to_lower('WORLD')}'")
    print(f"   to_slug('Hello World!'): '{transformer.to_slug('Hello World!')}'")
    print(f"   mask('secret123'): '{transformer.mask('secret123')}'")
    print(f"   hash('password'): '{transformer.hash('password')[:16]}...'")
    print()

    # 3. DateTime Conversion
    print("3. DATETIME CONVERSION:")
    print("-" * 40)

    dt = transformer.to_datetime("2024-01-15 14:30:00")
    print(f"   From string: {dt}")

    dt2 = transformer.to_datetime(1705329000)
    print(f"   From timestamp: {dt2}")
    print()

    # 4. Transform with Result
    print("4. TRANSFORM WITH RESULT:")
    print("-" * 40)

    result = transformer.transform("42", "integer")
    print(f"   Success: {result.success}")
    print(f"   Data: {result.data}")
    print(f"   Duration: {result.duration_ms:.3f}ms")

    error_result = transformer.transform("not-a-number", "integer")
    print(f"   Error case: {error_result.error}")
    print()

    # 5. Chain Transformer
    print("5. CHAIN TRANSFORMER:")
    print("-" * 40)

    chain = ChainTransformer(
        TrimTransformer(),
        LowerTransformer(),
        SlugTransformer()
    )

    result = chain.transform("  Hello World!  ")
    print(f"   Input: '  Hello World!  '")
    print(f"   Output: '{result}'")
    print()

    # 6. Conditional Transformer
    print("6. CONDITIONAL TRANSFORMER:")
    print("-" * 40)

    cond = ConditionalTransformer(
        condition=lambda x: isinstance(x, str) and x.isdigit(),
        if_true=IntegerTransformer(),
        if_false=StringTransformer()
    )

    print(f"   '123' -> {cond.transform('123')} (type: {type(cond.transform('123')).__name__})")
    print(f"   'abc' -> {cond.transform('abc')} (type: {type(cond.transform('abc')).__name__})")
    print()

    # 7. Data Mapper
    print("7. DATA MAPPER:")
    print("-" * 40)

    mapper = transformer.create_mapper()
    mapper.register_transformer("upper", UpperTransformer())

    mapper.add_mapping(FieldMapping(
        source="user.first_name",
        target="firstName",
        transformer="upper"
    ))
    mapper.add_mapping(FieldMapping(
        source="user.last_name",
        target="lastName"
    ))
    mapper.add_mapping(FieldMapping(
        source="user.email",
        target="contact.email"
    ))

    source_data = {
        "user": {
            "first_name": "john",
            "last_name": "Doe",
            "email": "john@example.com"
        }
    }

    mapped = mapper.map(source_data)
    print(f"   Source: {source_data}")
    print(f"   Mapped: {mapped}")
    print()

    # 8. Transform Pipeline
    print("8. TRANSFORM PIPELINE:")
    print("-" * 40)

    pipeline = (
        transformer.create_pipeline("text_processor")
        .add_step("trim", TrimTransformer())
        .add_step("lower", LowerTransformer())
        .add_step("slug", SlugTransformer())
    )

    result = pipeline.transform("  My Amazing Title!  ")
    print(f"   Input: '  My Amazing Title!  '")
    print(f"   Output: '{result.data}'")
    print(f"   Duration: {result.duration_ms:.3f}ms")
    print()

    # 9. Reversible Transforms
    print("9. REVERSIBLE TRANSFORMS:")
    print("-" * 40)

    dt_trans = DateTimeTransformer(format="%Y-%m-%d")

    forward = dt_trans.transform("2024-01-15")
    reverse = dt_trans.reverse(forward)

    print(f"   Forward: '2024-01-15' -> {forward}")
    print(f"   Reverse: {forward} -> '{reverse}'")
    print()

    # 10. Batch Transform
    print("10. BATCH TRANSFORM:")
    print("-" * 40)

    numbers = ["1", "2", "3", "4", "5"]
    results = transformer.batch_transform(numbers, "integer", batch_size=2)

    print(f"   Input: {numbers}")
    print(f"   Output: {[r.data for r in results if r.success]}")
    print(f"   All successful: {all(r.success for r in results)}")
    print()

    # 11. Default Transformer
    print("11. DEFAULT TRANSFORMER:")
    print("-" * 40)

    default_trans = DefaultTransformer(
        default="N/A",
        inner=UpperTransformer()
    )

    print(f"   None -> '{default_trans.transform(None)}'")
    print(f"   'hello' -> '{default_trans.transform('hello')}'")
    print()

    # 12. List with Item Transform
    print("12. LIST WITH ITEM TRANSFORM:")
    print("-" * 40)

    list_trans = ListTransformer(item_transformer=IntegerTransformer())

    result = list_trans.transform(["1", "2", "3"])
    print(f"   ['1', '2', '3'] -> {result}")
    print(f"   Types: {[type(x).__name__ for x in result]}")
    print()

    # 13. Pipeline Error Handling
    print("13. PIPELINE ERROR HANDLING:")
    print("-" * 40)

    error_pipeline = (
        transformer.create_pipeline("risky")
        .add_step("int", IntegerTransformer())
        .add_step("string", StringTransformer())
    )

    # Strict mode
    result = error_pipeline.transform("not-a-number", TransformStrategy.STRICT)
    print(f"   Strict mode error: {result.error}")

    # Lenient mode
    result = error_pipeline.transform("not-a-number", TransformStrategy.LENIENT)
    print(f"   Lenient mode warnings: {result.warnings}")
    print()

    # 14. Registered Pipeline
    print("14. REGISTERED PIPELINE:")
    print("-" * 40)

    transformer.register_pipeline("text_clean", pipeline)
    result = transformer.run_pipeline("  Another Test!  ", "text_clean")
    print(f"   Result: '{result.data}'")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = transformer.get_stats()
    print(f"   Total transforms: {stats.total_transforms}")
    print(f"   Successful: {stats.successful}")
    print(f"   Failed: {stats.failed}")

    print(f"\n   Available transformers: {transformer.list_transformers()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Transformer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
