#!/usr/bin/env python3
"""
BAEL - Data Export Manager
Comprehensive data export and transformation system.

Features:
- Multiple export formats (CSV, JSON, XML, Excel-like)
- Streaming exports
- Data transformation
- Column mapping
- Filtering
- Aggregation
- Pagination
- Compression
- Scheduling
- Progress tracking
"""

import asyncio
import base64
import csv
import gzip
import io
import json
import logging
import time
import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, AsyncIterator, Callable, Dict, Generic, Iterator,
                    List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ExportFormat(Enum):
    """Export formats."""
    CSV = "csv"
    JSON = "json"
    JSON_LINES = "jsonl"
    XML = "xml"
    TSV = "tsv"
    HTML = "html"
    MARKDOWN = "markdown"
    SQL = "sql"


class CompressionType(Enum):
    """Compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


class ExportStatus(Enum):
    """Export status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
# DATA STRUCTURES
# =============================================================================

@dataclass
class ColumnMapping:
    """Column mapping configuration."""
    source: str
    target: str
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None
    format_str: Optional[str] = None


@dataclass
class ExportOptions:
    """Export options."""
    format: ExportFormat = ExportFormat.CSV
    compression: CompressionType = CompressionType.NONE
    columns: List[str] = field(default_factory=list)
    column_mappings: List[ColumnMapping] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: Optional[str] = None
    sort_desc: bool = False
    limit: Optional[int] = None
    offset: int = 0
    include_header: bool = True
    delimiter: str = ","
    encoding: str = "utf-8"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    null_value: str = ""
    quote_char: str = '"'
    escape_char: str = "\\"
    line_ending: str = "\n"


@dataclass
class ExportJob:
    """Export job."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    options: ExportOptions = field(default_factory=ExportOptions)
    status: ExportStatus = ExportStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_rows: int = 0
    processed_rows: int = 0
    output_size: int = 0
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        """Get progress percentage."""
        if self.total_rows == 0:
            return 0.0

        return (self.processed_rows / self.total_rows) * 100

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if not self.started_at:
            return None

        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()


@dataclass
class ExportResult:
    """Export result."""
    job: ExportJob
    data: Optional[bytes] = None
    filename: str = ""
    mime_type: str = "application/octet-stream"


# =============================================================================
# FORMATTERS
# =============================================================================

class ExportFormatter(ABC):
    """Abstract export formatter."""

    @abstractmethod
    def format_header(self, columns: List[str]) -> bytes:
        """Format header."""
        pass

    @abstractmethod
    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format single row."""
        pass

    @abstractmethod
    def format_footer(self) -> bytes:
        """Format footer."""
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """Get MIME type."""
        pass

    @property
    @abstractmethod
    def extension(self) -> str:
        """Get file extension."""
        pass


class CSVFormatter(ExportFormatter):
    """CSV formatter."""

    def __init__(self, options: ExportOptions):
        self.options = options
        self._buffer = io.StringIO()
        self._writer = csv.writer(
            self._buffer,
            delimiter=options.delimiter,
            quotechar=options.quote_char,
            quoting=csv.QUOTE_MINIMAL
        )

    def format_header(self, columns: List[str]) -> bytes:
        """Format CSV header."""
        if not self.options.include_header:
            return b""

        self._buffer.seek(0)
        self._buffer.truncate()
        self._writer.writerow(columns)
        return self._buffer.getvalue().encode(self.options.encoding)

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format CSV row."""
        self._buffer.seek(0)
        self._buffer.truncate()

        values = []

        for col in columns:
            value = row.get(col)

            if value is None:
                value = self.options.null_value

            elif isinstance(value, datetime):
                value = value.strftime(self.options.date_format)

            elif isinstance(value, (list, dict)):
                value = json.dumps(value)

            values.append(str(value))

        self._writer.writerow(values)
        return self._buffer.getvalue().encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format CSV footer."""
        return b""

    @property
    def mime_type(self) -> str:
        return "text/csv"

    @property
    def extension(self) -> str:
        return "csv"


class JSONFormatter(ExportFormatter):
    """JSON formatter."""

    def __init__(self, options: ExportOptions):
        self.options = options
        self._first_row = True

    def format_header(self, columns: List[str]) -> bytes:
        """Format JSON header."""
        self._first_row = True
        return b"[\n"

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format JSON row."""
        # Filter to specified columns
        if columns:
            filtered = {k: v for k, v in row.items() if k in columns}
        else:
            filtered = row

        # Convert datetime
        for key, value in filtered.items():
            if isinstance(value, datetime):
                filtered[key] = value.strftime(self.options.date_format)

        prefix = "  " if self._first_row else ",\n  "
        self._first_row = False

        json_str = json.dumps(filtered, ensure_ascii=False)
        return f"{prefix}{json_str}".encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format JSON footer."""
        return b"\n]"

    @property
    def mime_type(self) -> str:
        return "application/json"

    @property
    def extension(self) -> str:
        return "json"


class JSONLinesFormatter(ExportFormatter):
    """JSON Lines formatter."""

    def __init__(self, options: ExportOptions):
        self.options = options

    def format_header(self, columns: List[str]) -> bytes:
        """Format header (none for JSONL)."""
        return b""

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format JSONL row."""
        if columns:
            filtered = {k: v for k, v in row.items() if k in columns}
        else:
            filtered = row

        for key, value in filtered.items():
            if isinstance(value, datetime):
                filtered[key] = value.strftime(self.options.date_format)

        json_str = json.dumps(filtered, ensure_ascii=False)
        return f"{json_str}\n".encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format footer (none for JSONL)."""
        return b""

    @property
    def mime_type(self) -> str:
        return "application/jsonl"

    @property
    def extension(self) -> str:
        return "jsonl"


class XMLFormatter(ExportFormatter):
    """XML formatter."""

    def __init__(self, options: ExportOptions, root_element: str = "data", row_element: str = "row"):
        self.options = options
        self.root_element = root_element
        self.row_element = row_element

    def format_header(self, columns: List[str]) -> bytes:
        """Format XML header."""
        return f'<?xml version="1.0" encoding="{self.options.encoding}"?>\n<{self.root_element}>\n'.encode(self.options.encoding)

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format XML row."""
        element = ET.Element(self.row_element)

        for col in columns or row.keys():
            value = row.get(col)

            if value is None:
                value = ""

            elif isinstance(value, datetime):
                value = value.strftime(self.options.date_format)

            elif isinstance(value, (list, dict)):
                value = json.dumps(value)

            child = ET.SubElement(element, self._sanitize_tag(col))
            child.text = str(value)

        xml_str = ET.tostring(element, encoding='unicode')
        return f"  {xml_str}\n".encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format XML footer."""
        return f"</{self.root_element}>".encode(self.options.encoding)

    def _sanitize_tag(self, tag: str) -> str:
        """Sanitize tag name."""
        # Replace invalid characters
        tag = ''.join(c if c.isalnum() or c == '_' else '_' for c in tag)

        # Ensure starts with letter
        if tag and not tag[0].isalpha():
            tag = 'x_' + tag

        return tag or 'field'

    @property
    def mime_type(self) -> str:
        return "application/xml"

    @property
    def extension(self) -> str:
        return "xml"


class HTMLFormatter(ExportFormatter):
    """HTML table formatter."""

    def __init__(self, options: ExportOptions, title: str = "Export"):
        self.options = options
        self.title = title

    def format_header(self, columns: List[str]) -> bytes:
        """Format HTML header."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="{self.options.encoding}">
    <title>{self.title}</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
<table>
"""

        if self.options.include_header:
            html += "<thead><tr>"
            html += "".join(f"<th>{col}</th>" for col in columns)
            html += "</tr></thead>\n"

        html += "<tbody>\n"

        return html.encode(self.options.encoding)

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format HTML row."""
        html = "<tr>"

        for col in columns:
            value = row.get(col)

            if value is None:
                value = ""

            elif isinstance(value, datetime):
                value = value.strftime(self.options.date_format)

            html += f"<td>{value}</td>"

        html += "</tr>\n"

        return html.encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format HTML footer."""
        return b"</tbody>\n</table>\n</body>\n</html>"

    @property
    def mime_type(self) -> str:
        return "text/html"

    @property
    def extension(self) -> str:
        return "html"


class MarkdownFormatter(ExportFormatter):
    """Markdown table formatter."""

    def __init__(self, options: ExportOptions):
        self.options = options
        self._columns: List[str] = []

    def format_header(self, columns: List[str]) -> bytes:
        """Format Markdown header."""
        self._columns = columns

        if not self.options.include_header:
            return b""

        header = "| " + " | ".join(columns) + " |\n"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |\n"

        return (header + separator).encode(self.options.encoding)

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format Markdown row."""
        values = []

        for col in columns:
            value = row.get(col)

            if value is None:
                value = ""

            elif isinstance(value, datetime):
                value = value.strftime(self.options.date_format)

            # Escape pipe characters
            value = str(value).replace("|", "\\|")
            values.append(value)

        line = "| " + " | ".join(values) + " |\n"
        return line.encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format Markdown footer."""
        return b""

    @property
    def mime_type(self) -> str:
        return "text/markdown"

    @property
    def extension(self) -> str:
        return "md"


class SQLFormatter(ExportFormatter):
    """SQL INSERT formatter."""

    def __init__(self, options: ExportOptions, table_name: str = "data"):
        self.options = options
        self.table_name = table_name

    def format_header(self, columns: List[str]) -> bytes:
        """Format SQL header."""
        return b""

    def format_row(self, row: Dict[str, Any], columns: List[str]) -> bytes:
        """Format SQL INSERT statement."""
        values = []

        for col in columns:
            value = row.get(col)

            if value is None:
                values.append("NULL")

            elif isinstance(value, (int, float)):
                values.append(str(value))

            elif isinstance(value, datetime):
                values.append(f"'{value.strftime(self.options.date_format)}'")

            elif isinstance(value, bool):
                values.append("1" if value else "0")

            else:
                # Escape quotes
                escaped = str(value).replace("'", "''")
                values.append(f"'{escaped}'")

        col_names = ", ".join(columns)
        val_str = ", ".join(values)

        sql = f"INSERT INTO {self.table_name} ({col_names}) VALUES ({val_str});\n"
        return sql.encode(self.options.encoding)

    def format_footer(self) -> bytes:
        """Format SQL footer."""
        return b""

    @property
    def mime_type(self) -> str:
        return "application/sql"

    @property
    def extension(self) -> str:
        return "sql"


# =============================================================================
# DATA TRANSFORMER
# =============================================================================

class DataTransformer:
    """Data transformation utilities."""

    @staticmethod
    def apply_mappings(
        row: Dict[str, Any],
        mappings: List[ColumnMapping]
    ) -> Dict[str, Any]:
        """Apply column mappings to row."""
        if not mappings:
            return row

        result = {}

        for mapping in mappings:
            value = row.get(mapping.source, mapping.default)

            if mapping.transform:
                try:
                    value = mapping.transform(value)
                except Exception:
                    value = mapping.default

            if mapping.format_str and value is not None:
                try:
                    value = mapping.format_str.format(value=value)
                except Exception:
                    pass

            result[mapping.target] = value

        return result

    @staticmethod
    def filter_row(row: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if row matches filters."""
        for field, condition in filters.items():
            value = row.get(field)

            if isinstance(condition, dict):
                # Complex condition
                if "eq" in condition and value != condition["eq"]:
                    return False

                if "ne" in condition and value == condition["ne"]:
                    return False

                if "gt" in condition and not (value and value > condition["gt"]):
                    return False

                if "gte" in condition and not (value and value >= condition["gte"]):
                    return False

                if "lt" in condition and not (value and value < condition["lt"]):
                    return False

                if "lte" in condition and not (value and value <= condition["lte"]):
                    return False

                if "in" in condition and value not in condition["in"]:
                    return False

                if "contains" in condition:
                    if not value or condition["contains"] not in str(value):
                        return False

            else:
                # Simple equality
                if value != condition:
                    return False

        return True

    @staticmethod
    def aggregate(
        rows: List[Dict[str, Any]],
        group_by: List[str],
        aggregations: Dict[str, Tuple[str, AggregationType]]
    ) -> List[Dict[str, Any]]:
        """Aggregate rows."""
        groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)

        # Group rows
        for row in rows:
            key = tuple(row.get(col) for col in group_by)
            groups[key].append(row)

        results = []

        for key, group_rows in groups.items():
            result = {col: val for col, val in zip(group_by, key)}

            for target_col, (source_col, agg_type) in aggregations.items():
                values = [r.get(source_col) for r in group_rows if r.get(source_col) is not None]

                if not values:
                    result[target_col] = None
                    continue

                if agg_type == AggregationType.SUM:
                    result[target_col] = sum(values)

                elif agg_type == AggregationType.AVG:
                    result[target_col] = sum(values) / len(values)

                elif agg_type == AggregationType.MIN:
                    result[target_col] = min(values)

                elif agg_type == AggregationType.MAX:
                    result[target_col] = max(values)

                elif agg_type == AggregationType.COUNT:
                    result[target_col] = len(values)

                elif agg_type == AggregationType.FIRST:
                    result[target_col] = values[0] if values else None

                elif agg_type == AggregationType.LAST:
                    result[target_col] = values[-1] if values else None

            results.append(result)

        return results


# =============================================================================
# EXPORT MANAGER
# =============================================================================

class DataExportManager:
    """
    Comprehensive Data Export Manager for BAEL.

    Provides data export with multiple formats and transformations.
    """

    def __init__(self):
        self._jobs: Dict[str, ExportJob] = {}
        self._formatters: Dict[ExportFormat, Type[ExportFormatter]] = {
            ExportFormat.CSV: CSVFormatter,
            ExportFormat.JSON: JSONFormatter,
            ExportFormat.JSON_LINES: JSONLinesFormatter,
            ExportFormat.XML: XMLFormatter,
            ExportFormat.HTML: HTMLFormatter,
            ExportFormat.MARKDOWN: MarkdownFormatter,
            ExportFormat.SQL: SQLFormatter
        }

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    async def export(
        self,
        data: List[Dict[str, Any]],
        options: ExportOptions = None,
        job_name: str = None
    ) -> ExportResult:
        """Export data."""
        options = options or ExportOptions()

        # Create job
        job = ExportJob(
            name=job_name or f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            options=options,
            status=ExportStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_rows=len(data)
        )

        self._jobs[job.id] = job

        try:
            # Apply transformations
            processed_data = self._process_data(data, options)

            # Get columns
            columns = self._get_columns(processed_data, options)

            # Create formatter
            formatter = self._create_formatter(options)

            # Generate output
            output = io.BytesIO()

            output.write(formatter.format_header(columns))

            for row in processed_data:
                output.write(formatter.format_row(row, columns))
                job.processed_rows += 1

            output.write(formatter.format_footer())

            # Apply compression
            result_data = output.getvalue()

            if options.compression == CompressionType.GZIP:
                result_data = gzip.compress(result_data)

            job.output_size = len(result_data)
            job.status = ExportStatus.COMPLETED
            job.completed_at = datetime.utcnow()

            # Create result
            filename = f"{job.name}.{formatter.extension}"

            if options.compression == CompressionType.GZIP:
                filename += ".gz"

            return ExportResult(
                job=job,
                data=result_data,
                filename=filename,
                mime_type=formatter.mime_type
            )

        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            raise

    async def export_stream(
        self,
        data_iterator: AsyncIterator[Dict[str, Any]],
        options: ExportOptions = None,
        columns: List[str] = None
    ) -> AsyncIterator[bytes]:
        """Stream export."""
        options = options or ExportOptions()
        columns = columns or options.columns

        formatter = self._create_formatter(options)

        if columns:
            yield formatter.format_header(columns)

        row_count = 0

        async for row in data_iterator:
            if not columns:
                columns = list(row.keys())
                yield formatter.format_header(columns)

            # Apply transformations
            if options.column_mappings:
                row = DataTransformer.apply_mappings(row, options.column_mappings)

            # Apply filters
            if options.filters and not DataTransformer.filter_row(row, options.filters):
                continue

            yield formatter.format_row(row, columns)
            row_count += 1

            if options.limit and row_count >= options.limit:
                break

        yield formatter.format_footer()

    def _process_data(
        self,
        data: List[Dict[str, Any]],
        options: ExportOptions
    ) -> List[Dict[str, Any]]:
        """Process data with transformations."""
        result = data

        # Apply column mappings
        if options.column_mappings:
            result = [
                DataTransformer.apply_mappings(row, options.column_mappings)
                for row in result
            ]

        # Apply filters
        if options.filters:
            result = [
                row for row in result
                if DataTransformer.filter_row(row, options.filters)
            ]

        # Apply sorting
        if options.sort_by:
            result = sorted(
                result,
                key=lambda x: x.get(options.sort_by) or "",
                reverse=options.sort_desc
            )

        # Apply pagination
        if options.offset:
            result = result[options.offset:]

        if options.limit:
            result = result[:options.limit]

        return result

    def _get_columns(
        self,
        data: List[Dict[str, Any]],
        options: ExportOptions
    ) -> List[str]:
        """Get columns for export."""
        if options.columns:
            return options.columns

        if options.column_mappings:
            return [m.target for m in options.column_mappings]

        if data:
            return list(data[0].keys())

        return []

    def _create_formatter(self, options: ExportOptions) -> ExportFormatter:
        """Create formatter for format."""
        formatter_class = self._formatters.get(options.format)

        if not formatter_class:
            raise ValueError(f"Unsupported format: {options.format}")

        return formatter_class(options)

    # -------------------------------------------------------------------------
    # JOB MANAGEMENT
    # -------------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: ExportStatus = None,
        limit: int = 100
    ) -> List[ExportJob]:
        """List jobs."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel job."""
        job = self._jobs.get(job_id)

        if not job:
            return False

        if job.status in [ExportStatus.COMPLETED, ExportStatus.FAILED]:
            return False

        job.status = ExportStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        return True

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get export statistics."""
        total = len(self._jobs)
        by_status = defaultdict(int)
        by_format = defaultdict(int)
        total_rows = 0
        total_size = 0

        for job in self._jobs.values():
            by_status[job.status.value] += 1
            by_format[job.options.format.value] += 1
            total_rows += job.processed_rows
            total_size += job.output_size

        return {
            "total_jobs": total,
            "by_status": dict(by_status),
            "by_format": dict(by_format),
            "total_rows": total_rows,
            "total_size_bytes": total_size
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Export Manager."""
    print("=" * 70)
    print("BAEL - DATA EXPORT MANAGER DEMO")
    print("Comprehensive Data Export System")
    print("=" * 70)
    print()

    manager = DataExportManager()

    # Sample data
    data = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 28, "department": "Engineering", "salary": 85000, "joined": datetime(2020, 3, 15)},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 35, "department": "Sales", "salary": 72000, "joined": datetime(2019, 7, 22)},
        {"id": 3, "name": "Carol", "email": "carol@example.com", "age": 42, "department": "Engineering", "salary": 120000, "joined": datetime(2015, 1, 10)},
        {"id": 4, "name": "David", "email": "david@example.com", "age": 29, "department": "Marketing", "salary": 65000, "joined": datetime(2021, 9, 1)},
        {"id": 5, "name": "Eve", "email": "eve@example.com", "age": 31, "department": "Sales", "salary": 78000, "joined": datetime(2018, 4, 5)}
    ]

    # 1. CSV Export
    print("1. CSV EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data,
        ExportOptions(format=ExportFormat.CSV),
        job_name="employees_csv"
    )

    print(f"   Filename: {result.filename}")
    print(f"   Size: {len(result.data)} bytes")
    print(f"   Preview:")
    print("   " + result.data.decode()[:200].replace("\n", "\n   "))
    print()

    # 2. JSON Export
    print("2. JSON EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data,
        ExportOptions(format=ExportFormat.JSON),
        job_name="employees_json"
    )

    print(f"   Filename: {result.filename}")
    print(f"   Preview:")
    print("   " + result.data.decode()[:200].replace("\n", "\n   ") + "...")
    print()

    # 3. With Column Selection
    print("3. COLUMN SELECTION:")
    print("-" * 40)

    result = await manager.export(
        data,
        ExportOptions(
            format=ExportFormat.CSV,
            columns=["name", "email", "department"]
        )
    )

    print("   Selected columns: name, email, department")
    print("   " + result.data.decode()[:150].replace("\n", "\n   "))
    print()

    # 4. With Filtering
    print("4. FILTERING:")
    print("-" * 40)

    result = await manager.export(
        data,
        ExportOptions(
            format=ExportFormat.CSV,
            filters={"department": "Engineering"}
        )
    )

    print("   Filter: department = Engineering")
    print("   " + result.data.decode().replace("\n", "\n   "))
    print()

    # 5. With Column Mapping
    print("5. COLUMN MAPPING:")
    print("-" * 40)

    result = await manager.export(
        data,
        ExportOptions(
            format=ExportFormat.CSV,
            column_mappings=[
                ColumnMapping(source="name", target="Full Name"),
                ColumnMapping(source="email", target="Email Address"),
                ColumnMapping(
                    source="salary",
                    target="Annual Salary",
                    transform=lambda x: f"${x:,}"
                )
            ]
        )
    )

    print("   Mapped columns: Full Name, Email Address, Annual Salary")
    print("   " + result.data.decode()[:200].replace("\n", "\n   "))
    print()

    # 6. XML Export
    print("6. XML EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data[:2],
        ExportOptions(format=ExportFormat.XML)
    )

    print("   " + result.data.decode()[:300].replace("\n", "\n   "))
    print()

    # 7. HTML Export
    print("7. HTML EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data[:2],
        ExportOptions(
            format=ExportFormat.HTML,
            columns=["name", "department", "salary"]
        )
    )

    print(f"   Filename: {result.filename}")
    print(f"   Size: {len(result.data)} bytes")
    print(f"   MIME: {result.mime_type}")
    print()

    # 8. Markdown Export
    print("8. MARKDOWN EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data[:3],
        ExportOptions(
            format=ExportFormat.MARKDOWN,
            columns=["name", "department", "salary"]
        )
    )

    print("   " + result.data.decode().replace("\n", "\n   "))
    print()

    # 9. SQL Export
    print("9. SQL EXPORT:")
    print("-" * 40)

    result = await manager.export(
        data[:2],
        ExportOptions(
            format=ExportFormat.SQL,
            columns=["id", "name", "email"]
        )
    )

    print("   " + result.data.decode().replace("\n", "\n   "))
    print()

    # 10. With Compression
    print("10. COMPRESSED EXPORT:")
    print("-" * 40)

    uncompressed = await manager.export(data, ExportOptions(format=ExportFormat.JSON))
    compressed = await manager.export(
        data,
        ExportOptions(
            format=ExportFormat.JSON,
            compression=CompressionType.GZIP
        )
    )

    print(f"   Uncompressed: {len(uncompressed.data)} bytes")
    print(f"   Compressed: {len(compressed.data)} bytes")
    print(f"   Ratio: {len(compressed.data) / len(uncompressed.data):.2%}")
    print()

    # 11. Aggregation
    print("11. DATA AGGREGATION:")
    print("-" * 40)

    aggregated = DataTransformer.aggregate(
        data,
        group_by=["department"],
        aggregations={
            "avg_salary": ("salary", AggregationType.AVG),
            "employee_count": ("id", AggregationType.COUNT),
            "max_age": ("age", AggregationType.MAX)
        }
    )

    for row in aggregated:
        print(f"   {row['department']}: avg=${row['avg_salary']:,.0f}, count={row['employee_count']}, max_age={row['max_age']}")
    print()

    # 12. Job Statistics
    print("12. EXPORT STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total jobs: {stats['total_jobs']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   By format: {stats['by_format']}")
    print(f"   Total rows: {stats['total_rows']}")
    print(f"   Total size: {stats['total_size_bytes']} bytes")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Export Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
