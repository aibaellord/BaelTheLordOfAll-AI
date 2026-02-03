#!/usr/bin/env python3
"""
BAEL - Data Import Manager
Comprehensive data import and ingestion system.

Features:
- Multiple format support (CSV, JSON, XML, YAML)
- Schema validation
- Data transformation
- Streaming imports
- Batch processing
- Error handling and recovery
- Progress tracking
- Duplicate detection
- Data mapping
- Import scheduling
"""

import asyncio
import csv
import hashlib
import io
import json
import logging
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, AsyncIterator, BinaryIO, Callable, Dict, Generic,
                    Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ImportFormat(Enum):
    """Import formats."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    XML = "xml"
    YAML = "yaml"
    TSV = "tsv"
    AUTO = "auto"


class ImportStatus(Enum):
    """Import job status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationLevel(Enum):
    """Validation strictness level."""
    NONE = "none"
    LENIENT = "lenient"
    STRICT = "strict"


class DuplicateStrategy(Enum):
    """Duplicate handling strategy."""
    SKIP = "skip"
    REPLACE = "replace"
    MERGE = "merge"
    ERROR = "error"


class DataType(Enum):
    """Data types for schema."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    OBJECT = "object"
    ANY = "any"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FieldSchema:
    """Field schema definition."""
    name: str
    data_type: DataType = DataType.STRING
    required: bool = False
    default: Any = None
    validators: List[Callable[[Any], bool]] = field(default_factory=list)
    transformers: List[Callable[[Any], Any]] = field(default_factory=list)
    source_name: Optional[str] = None  # For mapping from different field names


@dataclass
class ImportSchema:
    """Import schema definition."""
    fields: List[FieldSchema]
    strict: bool = False
    allow_extra_fields: bool = True

    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Get field by name."""
        for field in self.fields:
            if field.name == name or field.source_name == name:
                return field

        return None


@dataclass
class ImportOptions:
    """Import options."""
    format: ImportFormat = ImportFormat.AUTO
    encoding: str = "utf-8"
    validation_level: ValidationLevel = ValidationLevel.LENIENT
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.SKIP
    batch_size: int = 1000
    skip_header: bool = False
    delimiter: str = ","
    quote_char: str = '"'
    null_values: List[str] = field(default_factory=lambda: ["", "null", "NULL", "None"])
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    on_error: str = "continue"  # continue, stop, skip


@dataclass
class ImportError:
    """Import error."""
    row: int
    field: Optional[str]
    message: str
    value: Any = None
    exception: Optional[str] = None


@dataclass
class ImportProgress:
    """Import progress."""
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    skipped_rows: int = 0
    duplicate_rows: int = 0
    elapsed_time: float = 0.0

    @property
    def percentage(self) -> float:
        """Get progress percentage."""
        if self.total_rows == 0:
            return 0.0

        return (self.processed_rows / self.total_rows) * 100

    @property
    def rows_per_second(self) -> float:
        """Get processing rate."""
        if self.elapsed_time == 0:
            return 0.0

        return self.processed_rows / self.elapsed_time


@dataclass
class ImportResult:
    """Import result."""
    job_id: str
    status: ImportStatus
    progress: ImportProgress
    errors: List[ImportError] = field(default_factory=list)
    data: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.progress.processed_rows == 0:
            return 0.0

        return (self.progress.successful_rows / self.progress.processed_rows) * 100


@dataclass
class ImportJob:
    """Import job."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ImportStatus = ImportStatus.PENDING
    format: ImportFormat = ImportFormat.AUTO
    source: str = ""
    schema: Optional[ImportSchema] = None
    options: ImportOptions = field(default_factory=ImportOptions)
    progress: ImportProgress = field(default_factory=ImportProgress)
    errors: List[ImportError] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FORMAT PARSERS
# =============================================================================

class FormatParser(ABC):
    """Abstract format parser."""

    @abstractmethod
    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse data and yield records."""
        pass

    @abstractmethod
    def parse_stream(self, stream: BinaryIO, options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse stream and yield records."""
        pass


class CSVParser(FormatParser):
    """CSV format parser."""

    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse CSV data."""
        if isinstance(data, bytes):
            data = data.decode(options.encoding)

        reader = csv.DictReader(
            io.StringIO(data),
            delimiter=options.delimiter,
            quotechar=options.quote_char
        )

        for row in reader:
            yield dict(row)

    def parse_stream(self, stream: BinaryIO, options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse CSV stream."""
        text_stream = io.TextIOWrapper(stream, encoding=options.encoding)

        reader = csv.DictReader(
            text_stream,
            delimiter=options.delimiter,
            quotechar=options.quote_char
        )

        for row in reader:
            yield dict(row)


class JSONParser(FormatParser):
    """JSON format parser."""

    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse JSON data."""
        if isinstance(data, bytes):
            data = data.decode(options.encoding)

        parsed = json.loads(data)

        if isinstance(parsed, list):
            for item in parsed:
                yield item
        else:
            yield parsed

    def parse_stream(self, stream: BinaryIO, options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse JSON stream."""
        data = stream.read().decode(options.encoding)
        yield from self.parse(data, options)


class JSONLParser(FormatParser):
    """JSON Lines format parser."""

    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse JSONL data."""
        if isinstance(data, bytes):
            data = data.decode(options.encoding)

        for line in data.strip().split('\n'):
            if line.strip():
                yield json.loads(line)

    def parse_stream(self, stream: BinaryIO, options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse JSONL stream."""
        for line in stream:
            line_text = line.decode(options.encoding).strip()

            if line_text:
                yield json.loads(line_text)


class XMLParser(FormatParser):
    """XML format parser."""

    def __init__(self, row_tag: str = "item"):
        self.row_tag = row_tag

    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse XML data."""
        if isinstance(data, bytes):
            data = data.decode(options.encoding)

        root = ET.fromstring(data)

        for element in root.iter(self.row_tag):
            record = {}

            for child in element:
                record[child.tag] = child.text

            yield record

    def parse_stream(self, stream: BinaryIO, options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse XML stream."""
        data = stream.read().decode(options.encoding)
        yield from self.parse(data, options)


class TSVParser(CSVParser):
    """TSV format parser."""

    def parse(self, data: Union[str, bytes], options: ImportOptions) -> Iterator[Dict[str, Any]]:
        """Parse TSV data."""
        options.delimiter = "\t"
        yield from super().parse(data, options)


# =============================================================================
# DATA VALIDATOR
# =============================================================================

class DataValidator:
    """Data validator."""

    def __init__(self, schema: Optional[ImportSchema] = None):
        self.schema = schema
        self._type_validators: Dict[DataType, Callable[[Any], bool]] = {
            DataType.STRING: lambda v: True,
            DataType.INTEGER: self._is_integer,
            DataType.FLOAT: self._is_float,
            DataType.BOOLEAN: self._is_boolean,
            DataType.DATE: self._is_date,
            DataType.DATETIME: self._is_datetime,
            DataType.LIST: lambda v: isinstance(v, list),
            DataType.OBJECT: lambda v: isinstance(v, dict),
            DataType.ANY: lambda v: True
        }

    def validate(
        self,
        record: Dict[str, Any],
        options: ImportOptions
    ) -> Tuple[bool, List[ImportError]]:
        """Validate record against schema."""
        errors = []

        if not self.schema:
            return True, errors

        # Check required fields
        for field in self.schema.fields:
            if field.required:
                field_name = field.source_name or field.name

                if field_name not in record or record[field_name] in options.null_values:
                    errors.append(ImportError(
                        row=0,
                        field=field.name,
                        message=f"Required field '{field.name}' is missing"
                    ))

        # Validate field types
        for field in self.schema.fields:
            field_name = field.source_name or field.name

            if field_name in record:
                value = record[field_name]

                if value not in options.null_values:
                    # Type validation
                    validator = self._type_validators.get(field.data_type)

                    if validator and not validator(value):
                        errors.append(ImportError(
                            row=0,
                            field=field.name,
                            message=f"Invalid type for '{field.name}', expected {field.data_type.value}",
                            value=value
                        ))

                    # Custom validators
                    for custom_validator in field.validators:
                        try:
                            if not custom_validator(value):
                                errors.append(ImportError(
                                    row=0,
                                    field=field.name,
                                    message=f"Validation failed for '{field.name}'",
                                    value=value
                                ))
                        except Exception as e:
                            errors.append(ImportError(
                                row=0,
                                field=field.name,
                                message=f"Validator error for '{field.name}': {e}",
                                value=value,
                                exception=str(e)
                            ))

        # Check extra fields
        if self.schema.strict and not self.schema.allow_extra_fields:
            schema_fields = {f.source_name or f.name for f in self.schema.fields}

            for field_name in record:
                if field_name not in schema_fields:
                    errors.append(ImportError(
                        row=0,
                        field=field_name,
                        message=f"Unexpected field '{field_name}'"
                    ))

        is_valid = len(errors) == 0 or options.validation_level == ValidationLevel.LENIENT

        return is_valid, errors

    def _is_integer(self, value: Any) -> bool:
        """Check if value is integer."""
        if isinstance(value, int) and not isinstance(value, bool):
            return True

        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False

        return False

    def _is_float(self, value: Any) -> bool:
        """Check if value is float."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True

        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False

        return False

    def _is_boolean(self, value: Any) -> bool:
        """Check if value is boolean."""
        if isinstance(value, bool):
            return True

        if isinstance(value, str):
            return value.lower() in ('true', 'false', 'yes', 'no', '1', '0')

        return False

    def _is_date(self, value: Any) -> bool:
        """Check if value is date."""
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
                return True
            except ValueError:
                pass

        return False

    def _is_datetime(self, value: Any) -> bool:
        """Check if value is datetime."""
        if isinstance(value, datetime):
            return True

        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                pass

        return False


# =============================================================================
# DATA TRANSFORMER
# =============================================================================

class DataTransformer:
    """Data transformer."""

    def __init__(self, schema: Optional[ImportSchema] = None):
        self.schema = schema
        self._type_converters: Dict[DataType, Callable[[Any], Any]] = {
            DataType.STRING: str,
            DataType.INTEGER: self._to_integer,
            DataType.FLOAT: self._to_float,
            DataType.BOOLEAN: self._to_boolean,
            DataType.DATE: self._to_date,
            DataType.DATETIME: self._to_datetime,
            DataType.LIST: self._to_list,
            DataType.OBJECT: self._to_object,
            DataType.ANY: lambda v: v
        }

    def transform(
        self,
        record: Dict[str, Any],
        options: ImportOptions
    ) -> Dict[str, Any]:
        """Transform record according to schema."""
        if not self.schema:
            return self._apply_null_values(record, options)

        result = {}

        for field in self.schema.fields:
            source_name = field.source_name or field.name

            if source_name in record:
                value = record[source_name]

                # Handle null values
                if value in options.null_values:
                    value = field.default
                else:
                    # Type conversion
                    converter = self._type_converters.get(field.data_type)

                    if converter:
                        try:
                            value = converter(value)
                        except Exception:
                            value = field.default

                    # Custom transformers
                    for transformer in field.transformers:
                        try:
                            value = transformer(value)
                        except Exception:
                            pass

                result[field.name] = value

            elif field.default is not None:
                result[field.name] = field.default

        # Include extra fields if allowed
        if self.schema.allow_extra_fields:
            schema_fields = {f.source_name or f.name for f in self.schema.fields}

            for key, value in record.items():
                if key not in schema_fields and key not in result:
                    result[key] = value

        return result

    def _apply_null_values(
        self,
        record: Dict[str, Any],
        options: ImportOptions
    ) -> Dict[str, Any]:
        """Apply null value handling."""
        return {
            k: (None if v in options.null_values else v)
            for k, v in record.items()
        }

    def _to_integer(self, value: Any) -> int:
        """Convert to integer."""
        if isinstance(value, int) and not isinstance(value, bool):
            return value

        return int(float(str(value)))

    def _to_float(self, value: Any) -> float:
        """Convert to float."""
        return float(value)

    def _to_boolean(self, value: Any) -> bool:
        """Convert to boolean."""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1')

        return bool(value)

    def _to_date(self, value: Any) -> str:
        """Convert to date string."""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")

        return str(value)

    def _to_datetime(self, value: Any) -> datetime:
        """Convert to datetime."""
        if isinstance(value, datetime):
            return value

        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))

    def _to_list(self, value: Any) -> list:
        """Convert to list."""
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(',')

        return [value]

    def _to_object(self, value: Any) -> dict:
        """Convert to object."""
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            return json.loads(value)

        return {"value": value}


# =============================================================================
# DUPLICATE DETECTOR
# =============================================================================

class DuplicateDetector:
    """Duplicate detector."""

    def __init__(self, key_fields: List[str] = None):
        self.key_fields = key_fields or []
        self._seen: Set[str] = set()

    def get_key(self, record: Dict[str, Any]) -> str:
        """Get record key for duplicate detection."""
        if self.key_fields:
            key_values = [str(record.get(f, "")) for f in self.key_fields]
            key_str = "|".join(key_values)
        else:
            key_str = json.dumps(record, sort_keys=True)

        return hashlib.md5(key_str.encode()).hexdigest()

    def is_duplicate(self, record: Dict[str, Any]) -> bool:
        """Check if record is duplicate."""
        key = self.get_key(record)

        if key in self._seen:
            return True

        self._seen.add(key)
        return False

    def reset(self):
        """Reset detector."""
        self._seen.clear()


# =============================================================================
# DATA IMPORT MANAGER
# =============================================================================

class DataImportManager:
    """
    Comprehensive Data Import Manager for BAEL.

    Provides data import with multiple formats and validation.
    """

    def __init__(self):
        self._parsers: Dict[ImportFormat, FormatParser] = {
            ImportFormat.CSV: CSVParser(),
            ImportFormat.JSON: JSONParser(),
            ImportFormat.JSONL: JSONLParser(),
            ImportFormat.XML: XMLParser(),
            ImportFormat.TSV: TSVParser()
        }

        self._jobs: Dict[str, ImportJob] = {}
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # FORMAT DETECTION
    # -------------------------------------------------------------------------

    def detect_format(self, data: Union[str, bytes]) -> ImportFormat:
        """Detect data format."""
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')

        data = data.strip()

        # JSON detection
        if data.startswith('[') or data.startswith('{'):
            return ImportFormat.JSON

        # XML detection
        if data.startswith('<?xml') or data.startswith('<'):
            return ImportFormat.XML

        # JSONL detection (each line is JSON)
        first_line = data.split('\n')[0].strip()

        if first_line.startswith('{'):
            return ImportFormat.JSONL

        # TSV detection
        if '\t' in first_line and ',' not in first_line:
            return ImportFormat.TSV

        # Default to CSV
        return ImportFormat.CSV

    # -------------------------------------------------------------------------
    # IMPORT OPERATIONS
    # -------------------------------------------------------------------------

    async def import_data(
        self,
        data: Union[str, bytes],
        schema: Optional[ImportSchema] = None,
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """Import data from string or bytes."""
        options = options or ImportOptions()

        # Detect format if auto
        if options.format == ImportFormat.AUTO:
            options.format = self.detect_format(data)

        # Create job
        job = ImportJob(
            format=options.format,
            source="memory",
            schema=schema,
            options=options
        )

        self._jobs[job.id] = job

        return await self._process_import(job, data)

    async def import_file(
        self,
        path: str,
        schema: Optional[ImportSchema] = None,
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """Import data from file."""
        options = options or ImportOptions()

        with open(path, 'rb') as f:
            data = f.read()

        # Detect format if auto
        if options.format == ImportFormat.AUTO:
            ext = os.path.splitext(path)[1].lower()
            format_map = {
                '.csv': ImportFormat.CSV,
                '.json': ImportFormat.JSON,
                '.jsonl': ImportFormat.JSONL,
                '.xml': ImportFormat.XML,
                '.tsv': ImportFormat.TSV
            }

            options.format = format_map.get(ext, self.detect_format(data))

        # Create job
        job = ImportJob(
            format=options.format,
            source=path,
            schema=schema,
            options=options
        )

        self._jobs[job.id] = job

        return await self._process_import(job, data)

    async def import_stream(
        self,
        stream: AsyncIterator[bytes],
        schema: Optional[ImportSchema] = None,
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """Import data from async stream."""
        options = options or ImportOptions()

        # Collect all chunks
        chunks = []

        async for chunk in stream:
            chunks.append(chunk)

        data = b''.join(chunks)

        return await self.import_data(data, schema, options)

    async def _process_import(
        self,
        job: ImportJob,
        data: Union[str, bytes]
    ) -> ImportResult:
        """Process import job."""
        job.status = ImportStatus.RUNNING
        job.started_at = datetime.utcnow()
        start_time = time.time()

        validator = DataValidator(job.schema)
        transformer = DataTransformer(job.schema)
        duplicate_detector = DuplicateDetector()

        result_data = []
        errors = []

        try:
            parser = self._parsers.get(job.options.format)

            if not parser:
                raise ValueError(f"Unsupported format: {job.options.format}")

            # Parse and process records
            row_num = 0

            for record in parser.parse(data, job.options):
                row_num += 1
                job.progress.total_rows = row_num
                job.progress.processed_rows = row_num

                # Check duplicates
                if duplicate_detector.is_duplicate(record):
                    if job.options.duplicate_strategy == DuplicateStrategy.SKIP:
                        job.progress.duplicate_rows += 1
                        job.progress.skipped_rows += 1
                        continue

                    elif job.options.duplicate_strategy == DuplicateStrategy.ERROR:
                        errors.append(ImportError(
                            row=row_num,
                            field=None,
                            message="Duplicate record detected"
                        ))

                        if job.options.on_error == "stop":
                            break
                        continue

                # Validate
                is_valid, validation_errors = validator.validate(record, job.options)

                for err in validation_errors:
                    err.row = row_num
                    errors.append(err)

                if not is_valid:
                    job.progress.failed_rows += 1

                    if job.options.on_error == "stop":
                        break
                    continue

                # Transform
                try:
                    transformed = transformer.transform(record, job.options)
                    result_data.append(transformed)
                    job.progress.successful_rows += 1

                except Exception as e:
                    errors.append(ImportError(
                        row=row_num,
                        field=None,
                        message=f"Transform error: {e}",
                        exception=str(e)
                    ))
                    job.progress.failed_rows += 1

                    if job.options.on_error == "stop":
                        break

                # Trigger progress callbacks
                await self._trigger_callbacks('progress', job)

            job.status = ImportStatus.COMPLETED

        except Exception as e:
            job.status = ImportStatus.FAILED
            errors.append(ImportError(
                row=0,
                field=None,
                message=f"Import failed: {e}",
                exception=str(e)
            ))

            logger.error(f"Import failed: {e}")

        job.completed_at = datetime.utcnow()
        job.progress.elapsed_time = time.time() - start_time
        job.errors = errors

        self._stats["imports"] += 1
        self._stats["rows_imported"] += job.progress.successful_rows

        return ImportResult(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            errors=errors,
            data=result_data,
            started_at=job.started_at,
            completed_at=job.completed_at
        )

    # -------------------------------------------------------------------------
    # BATCH IMPORT
    # -------------------------------------------------------------------------

    async def import_batch(
        self,
        items: List[Union[str, bytes]],
        schema: Optional[ImportSchema] = None,
        options: Optional[ImportOptions] = None
    ) -> List[ImportResult]:
        """Import multiple data items."""
        results = []

        for item in items:
            result = await self.import_data(item, schema, options)
            results.append(result)

        return results

    # -------------------------------------------------------------------------
    # STREAMING IMPORT
    # -------------------------------------------------------------------------

    async def import_streaming(
        self,
        data: Union[str, bytes],
        schema: Optional[ImportSchema] = None,
        options: Optional[ImportOptions] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream import records one at a time."""
        options = options or ImportOptions()

        if options.format == ImportFormat.AUTO:
            options.format = self.detect_format(data)

        parser = self._parsers.get(options.format)

        if not parser:
            raise ValueError(f"Unsupported format: {options.format}")

        transformer = DataTransformer(schema)

        for record in parser.parse(data, options):
            try:
                yield transformer.transform(record, options)
            except Exception:
                if options.on_error == "stop":
                    break

    # -------------------------------------------------------------------------
    # JOB MANAGEMENT
    # -------------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[ImportJob]:
        """Get import job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[ImportStatus] = None
    ) -> List[ImportJob]:
        """List import jobs."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel import job."""
        job = self._jobs.get(job_id)

        if not job or job.status not in (ImportStatus.PENDING, ImportStatus.RUNNING):
            return False

        job.status = ImportStatus.CANCELLED

        return True

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_progress(self, callback: Callable[[ImportJob], None]):
        """Register progress callback."""
        self._callbacks['progress'].append(callback)

    def on_complete(self, callback: Callable[[ImportResult], None]):
        """Register completion callback."""
        self._callbacks['complete'].append(callback)

    async def _trigger_callbacks(self, event: str, data: Any):
        """Trigger callbacks for event."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def create_schema(
        self,
        fields: Dict[str, DataType],
        required: List[str] = None
    ) -> ImportSchema:
        """Create import schema from field definitions."""
        required = required or []

        schema_fields = [
            FieldSchema(
                name=name,
                data_type=dtype,
                required=name in required
            )
            for name, dtype in fields.items()
        ]

        return ImportSchema(fields=schema_fields)

    def get_stats(self) -> Dict[str, Any]:
        """Get import statistics."""
        return {
            "total_imports": self._stats["imports"],
            "total_rows_imported": self._stats["rows_imported"],
            "active_jobs": len([j for j in self._jobs.values() if j.status == ImportStatus.RUNNING])
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Import Manager."""
    print("=" * 70)
    print("BAEL - DATA IMPORT MANAGER DEMO")
    print("Comprehensive Data Import System")
    print("=" * 70)
    print()

    manager = DataImportManager()

    # 1. CSV Import
    print("1. CSV IMPORT:")
    print("-" * 40)

    csv_data = """name,age,email,active
John Doe,30,john@example.com,true
Jane Smith,25,jane@example.com,true
Bob Wilson,35,bob@example.com,false
Alice Brown,28,alice@example.com,true"""

    result = await manager.import_data(csv_data)

    print(f"   Status: {result.status.value}")
    print(f"   Rows imported: {result.progress.successful_rows}")
    print(f"   Time: {result.progress.elapsed_time:.3f}s")
    print(f"   First record: {result.data[0]}")
    print()

    # 2. JSON Import
    print("2. JSON IMPORT:")
    print("-" * 40)

    json_data = json.dumps([
        {"id": 1, "name": "Product A", "price": 29.99},
        {"id": 2, "name": "Product B", "price": 49.99},
        {"id": 3, "name": "Product C", "price": 19.99}
    ])

    result = await manager.import_data(json_data)

    print(f"   Status: {result.status.value}")
    print(f"   Rows imported: {result.progress.successful_rows}")
    print(f"   Data: {result.data}")
    print()

    # 3. JSONL Import
    print("3. JSONL IMPORT:")
    print("-" * 40)

    jsonl_data = """{"event": "click", "timestamp": 1234567890}
{"event": "view", "timestamp": 1234567891}
{"event": "purchase", "timestamp": 1234567892}"""

    result = await manager.import_data(jsonl_data, options=ImportOptions(format=ImportFormat.JSONL))

    print(f"   Status: {result.status.value}")
    print(f"   Events imported: {result.progress.successful_rows}")
    print()

    # 4. Schema Validation
    print("4. SCHEMA VALIDATION:")
    print("-" * 40)

    schema = manager.create_schema(
        fields={
            "name": DataType.STRING,
            "age": DataType.INTEGER,
            "email": DataType.STRING,
            "active": DataType.BOOLEAN
        },
        required=["name", "email"]
    )

    result = await manager.import_data(csv_data, schema=schema)

    print(f"   Status: {result.status.value}")
    print(f"   Valid rows: {result.progress.successful_rows}")
    print(f"   Errors: {len(result.errors)}")

    if result.data:
        print(f"   Transformed: {result.data[0]}")
    print()

    # 5. Data with Errors
    print("5. DATA WITH ERRORS:")
    print("-" * 40)

    bad_csv = """name,age,email
John,thirty,john@example.com
Jane,25,jane@example.com
,40,missing@example.com"""

    schema = manager.create_schema(
        fields={
            "name": DataType.STRING,
            "age": DataType.INTEGER,
            "email": DataType.STRING
        },
        required=["name"]
    )

    result = await manager.import_data(
        bad_csv,
        schema=schema,
        options=ImportOptions(validation_level=ValidationLevel.STRICT)
    )

    print(f"   Status: {result.status.value}")
    print(f"   Successful: {result.progress.successful_rows}")
    print(f"   Failed: {result.progress.failed_rows}")
    print(f"   Errors: {len(result.errors)}")

    for error in result.errors[:3]:
        print(f"      Row {error.row}: {error.message}")
    print()

    # 6. Duplicate Detection
    print("6. DUPLICATE DETECTION:")
    print("-" * 40)

    dup_data = """id,name
1,Apple
2,Banana
1,Apple
3,Cherry
2,Banana"""

    result = await manager.import_data(
        dup_data,
        options=ImportOptions(duplicate_strategy=DuplicateStrategy.SKIP)
    )

    print(f"   Total rows: {result.progress.total_rows}")
    print(f"   Duplicates skipped: {result.progress.duplicate_rows}")
    print(f"   Imported: {result.progress.successful_rows}")
    print()

    # 7. Format Detection
    print("7. FORMAT DETECTION:")
    print("-" * 40)

    formats = [
        ('CSV', 'a,b,c\n1,2,3'),
        ('JSON', '[{"a": 1}]'),
        ('JSONL', '{"a": 1}\n{"b": 2}'),
        ('XML', '<root><item><a>1</a></item></root>'),
        ('TSV', 'a\tb\tc\n1\t2\t3')
    ]

    for name, data in formats:
        detected = manager.detect_format(data)
        print(f"   {name}: detected as {detected.value}")
    print()

    # 8. Field Mapping
    print("8. FIELD MAPPING:")
    print("-" * 40)

    old_format = """first_name,last_name,years_old
John,Doe,30
Jane,Smith,25"""

    schema = ImportSchema(fields=[
        FieldSchema(name="name", source_name="first_name"),
        FieldSchema(name="surname", source_name="last_name"),
        FieldSchema(name="age", source_name="years_old", data_type=DataType.INTEGER)
    ])

    result = await manager.import_data(old_format, schema=schema)

    print(f"   Mapped data: {result.data}")
    print()

    # 9. Streaming Import
    print("9. STREAMING IMPORT:")
    print("-" * 40)

    records = []

    async for record in manager.import_streaming(csv_data):
        records.append(record)
        print(f"   Streamed: {record['name']}")

    print(f"   Total streamed: {len(records)}")
    print()

    # 10. Custom Transformers
    print("10. CUSTOM TRANSFORMERS:")
    print("-" * 40)

    schema = ImportSchema(fields=[
        FieldSchema(
            name="name",
            transformers=[str.upper]
        ),
        FieldSchema(
            name="email",
            transformers=[str.lower]
        )
    ])

    data = """name,email
john doe,JOHN@EXAMPLE.COM
jane smith,JANE@EXAMPLE.COM"""

    result = await manager.import_data(data, schema=schema)

    for record in result.data:
        print(f"   {record['name']} - {record['email']}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total imports: {stats['total_imports']}")
    print(f"   Total rows: {stats['total_rows_imported']}")
    print()

    # 12. Job Management
    print("12. JOB MANAGEMENT:")
    print("-" * 40)

    jobs = manager.list_jobs()

    print(f"   Total jobs: {len(jobs)}")

    for job in jobs[:3]:
        print(f"      {job.id[:8]}... - {job.status.value} - {job.progress.successful_rows} rows")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Import Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
