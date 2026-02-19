"""
BAEL Export Engine
===================

Export data in CSV, JSON, Excel, and other formats.

"Ba'el's wisdom manifests in every format." — Ba'el
"""

import asyncio
import logging
import uuid
import csv
import json
import io
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Iterator, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("BAEL.Export")


# ============================================================================
# ENUMS
# ============================================================================

class ExportFormat(Enum):
    """Export format."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"  # JSON Lines
    EXCEL = "excel"
    XML = "xml"
    YAML = "yaml"
    PARQUET = "parquet"
    TSV = "tsv"


class ExportStatus(Enum):
    """Export job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExportColumn:
    """A column definition for export."""
    name: str
    source: str  # Field path in data
    label: Optional[str] = None  # Display label
    formatter: Optional[Callable[[Any], str]] = None
    width: Optional[int] = None


@dataclass
class ExportOptions:
    """Export options."""
    format: ExportFormat = ExportFormat.CSV

    # Columns
    columns: Optional[List[ExportColumn]] = None
    include_headers: bool = True

    # CSV/TSV
    delimiter: str = ","
    quoting: int = csv.QUOTE_MINIMAL

    # JSON
    indent: Optional[int] = 2

    # Streaming
    chunk_size: int = 1000

    # Compression
    compress: bool = False

    # Encoding
    encoding: str = "utf-8"


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    format: ExportFormat

    # Output
    data: Optional[bytes] = None
    file_path: Optional[str] = None

    # Stats
    rows_exported: int = 0
    file_size: int = 0
    duration_ms: float = 0.0

    # Error
    error: Optional[str] = None


@dataclass
class ExportJob:
    """An export job."""
    id: str
    format: ExportFormat
    status: ExportStatus = ExportStatus.PENDING

    # Options
    options: ExportOptions = field(default_factory=ExportOptions)

    # Progress
    total_rows: int = 0
    processed_rows: int = 0

    # Result
    result: Optional[ExportResult] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExportConfig:
    """Export engine configuration."""
    default_format: ExportFormat = ExportFormat.CSV
    max_rows: int = 1000000
    temp_dir: str = "/tmp/exports"


# ============================================================================
# BASE EXPORTER
# ============================================================================

class BaseExporter:
    """Base class for exporters."""

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export data to bytes."""
        raise NotImplementedError

    def export_stream(
        self,
        data: Iterator[Dict],
        output: BinaryIO,
        options: ExportOptions
    ) -> int:
        """Export data to stream, return row count."""
        raise NotImplementedError

    def _get_value(
        self,
        row: Dict,
        source: str,
        formatter: Optional[Callable] = None
    ) -> Any:
        """Get value from row by source path."""
        value = row

        for part in source.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                value = None

            if value is None:
                break

        if formatter and value is not None:
            value = formatter(value)

        return value


# ============================================================================
# CSV EXPORTER
# ============================================================================

class CSVExporter(BaseExporter):
    """CSV exporter."""

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export to CSV bytes."""
        output = io.StringIO()
        self._export_to_file(data, output, options)
        return output.getvalue().encode(options.encoding)

    def export_stream(
        self,
        data: Iterator[Dict],
        output: BinaryIO,
        options: ExportOptions
    ) -> int:
        """Export to stream."""
        text_output = io.TextIOWrapper(output, encoding=options.encoding)
        return self._export_to_file(data, text_output, options)

    def _export_to_file(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        output: io.StringIO,
        options: ExportOptions
    ) -> int:
        """Export to file-like object."""
        delimiter = options.delimiter if options.format == ExportFormat.CSV else "\t"

        writer = csv.writer(
            output,
            delimiter=delimiter,
            quoting=options.quoting
        )

        # Determine columns from first row if not specified
        columns = options.columns
        first_row_written = False
        row_count = 0

        for row in data:
            # Auto-detect columns from first row
            if columns is None:
                columns = [
                    ExportColumn(name=k, source=k)
                    for k in row.keys()
                ]

            # Write headers
            if options.include_headers and not first_row_written:
                headers = [c.label or c.name for c in columns]
                writer.writerow(headers)
                first_row_written = True

            # Write data row
            values = [
                self._get_value(row, c.source, c.formatter)
                for c in columns
            ]
            writer.writerow(values)
            row_count += 1

        return row_count


# ============================================================================
# JSON EXPORTER
# ============================================================================

class JSONExporter(BaseExporter):
    """JSON exporter."""

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export to JSON bytes."""
        if options.format == ExportFormat.JSONL:
            return self._export_jsonl(data, options)
        else:
            return self._export_json(data, options)

    def _export_json(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export as JSON array."""
        # Convert iterator to list
        if not isinstance(data, list):
            data = list(data)

        # Apply column transformations
        if options.columns:
            data = [
                {
                    c.label or c.name: self._get_value(row, c.source, c.formatter)
                    for c in options.columns
                }
                for row in data
            ]

        result = json.dumps(data, indent=options.indent, default=str)
        return result.encode(options.encoding)

    def _export_jsonl(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export as JSON Lines."""
        lines = []

        for row in data:
            if options.columns:
                row = {
                    c.label or c.name: self._get_value(row, c.source, c.formatter)
                    for c in options.columns
                }

            lines.append(json.dumps(row, default=str))

        return '\n'.join(lines).encode(options.encoding)

    def export_stream(
        self,
        data: Iterator[Dict],
        output: BinaryIO,
        options: ExportOptions
    ) -> int:
        """Export to stream."""
        row_count = 0

        for row in data:
            if options.columns:
                row = {
                    c.label or c.name: self._get_value(row, c.source, c.formatter)
                    for c in options.columns
                }

            line = json.dumps(row, default=str) + '\n'
            output.write(line.encode(options.encoding))
            row_count += 1

        return row_count


# ============================================================================
# EXCEL EXPORTER
# ============================================================================

class ExcelExporter(BaseExporter):
    """Excel exporter (creates simple XML spreadsheet)."""

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export to Excel XML format."""
        output = io.StringIO()

        # XML header
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<?mso-application progid="Excel.Sheet"?>\n')
        output.write('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"\n')
        output.write('  xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n')
        output.write('  <Worksheet ss:Name="Sheet1">\n')
        output.write('    <Table>\n')

        # Determine columns
        columns = options.columns
        first_row = True

        for row in data:
            if columns is None:
                columns = [
                    ExportColumn(name=k, source=k)
                    for k in row.keys()
                ]

            # Write headers
            if options.include_headers and first_row:
                output.write('      <Row>\n')
                for col in columns:
                    label = self._escape_xml(col.label or col.name)
                    output.write(f'        <Cell><Data ss:Type="String">{label}</Data></Cell>\n')
                output.write('      </Row>\n')
                first_row = False

            # Write data row
            output.write('      <Row>\n')
            for col in columns:
                value = self._get_value(row, col.source, col.formatter)
                value_str = self._escape_xml(str(value) if value is not None else '')
                cell_type = self._get_cell_type(value)
                output.write(f'        <Cell><Data ss:Type="{cell_type}">{value_str}</Data></Cell>\n')
            output.write('      </Row>\n')

        # Close tags
        output.write('    </Table>\n')
        output.write('  </Worksheet>\n')
        output.write('</Workbook>\n')

        return output.getvalue().encode(options.encoding)

    def _escape_xml(self, value: str) -> str:
        """Escape XML special characters."""
        return (
            value
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )

    def _get_cell_type(self, value: Any) -> str:
        """Get Excel cell type."""
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, (int, float)):
            return "Number"
        elif isinstance(value, datetime):
            return "DateTime"
        else:
            return "String"

    def export_stream(
        self,
        data: Iterator[Dict],
        output: BinaryIO,
        options: ExportOptions
    ) -> int:
        """Export to stream."""
        result = self.export(data, options)
        output.write(result)
        return result.count(b'<Row>') - (1 if options.include_headers else 0)


# ============================================================================
# XML EXPORTER
# ============================================================================

class XMLExporter(BaseExporter):
    """XML exporter."""

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        options: ExportOptions
    ) -> bytes:
        """Export to XML bytes."""
        output = io.StringIO()

        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<data>\n')

        for row in data:
            output.write('  <row>\n')

            if options.columns:
                for col in options.columns:
                    name = col.name
                    value = self._get_value(row, col.source, col.formatter)
                    value_str = self._escape_xml(str(value) if value is not None else '')
                    output.write(f'    <{name}>{value_str}</{name}>\n')
            else:
                for key, value in row.items():
                    value_str = self._escape_xml(str(value) if value is not None else '')
                    output.write(f'    <{key}>{value_str}</{key}>\n')

            output.write('  </row>\n')

        output.write('</data>\n')

        return output.getvalue().encode(options.encoding)

    def _escape_xml(self, value: str) -> str:
        """Escape XML special characters."""
        return (
            value
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )

    def export_stream(
        self,
        data: Iterator[Dict],
        output: BinaryIO,
        options: ExportOptions
    ) -> int:
        """Export to stream."""
        result = self.export(data, options)
        output.write(result)
        return result.count(b'<row>')


# ============================================================================
# MAIN EXPORT ENGINE
# ============================================================================

class ExportEngine:
    """
    Main export engine.

    Features:
    - Multiple formats (CSV, JSON, Excel, XML)
    - Streaming export
    - Column transformations
    - Background jobs

    "Ba'el's data flows in all forms." — Ba'el
    """

    def __init__(self, config: Optional[ExportConfig] = None):
        """Initialize export engine."""
        self.config = config or ExportConfig()

        # Exporters
        self._exporters: Dict[ExportFormat, BaseExporter] = {
            ExportFormat.CSV: CSVExporter(),
            ExportFormat.TSV: CSVExporter(),
            ExportFormat.JSON: JSONExporter(),
            ExportFormat.JSONL: JSONExporter(),
            ExportFormat.EXCEL: ExcelExporter(),
            ExportFormat.XML: XMLExporter(),
        }

        # Jobs
        self._jobs: Dict[str, ExportJob] = {}

        # Stats
        self._stats = defaultdict(int)

        self._lock = threading.RLock()

        logger.info("ExportEngine initialized")

    # ========================================================================
    # SYNCHRONOUS EXPORT
    # ========================================================================

    def export(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        format: ExportFormat = ExportFormat.CSV,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """
        Export data synchronously.

        Args:
            data: Data to export
            format: Export format
            options: Export options

        Returns:
            ExportResult
        """
        start_time = datetime.now()

        options = options or ExportOptions(format=format)
        options.format = format

        exporter = self._exporters.get(format)

        if not exporter:
            return ExportResult(
                success=False,
                format=format,
                error=f"Unsupported format: {format}"
            )

        try:
            # Convert to list to count rows
            if not isinstance(data, list):
                data = list(data)

            # Export
            output = exporter.export(data, options)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            self._stats['exports'] += 1
            self._stats[f'exports_{format.value}'] += 1

            return ExportResult(
                success=True,
                format=format,
                data=output,
                rows_exported=len(data),
                file_size=len(output),
                duration_ms=duration
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                format=format,
                error=str(e)
            )

    def export_to_file(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        file_path: str,
        format: Optional[ExportFormat] = None,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Export data to a file."""
        # Infer format from extension
        if format is None:
            ext = file_path.rsplit('.', 1)[-1].lower()
            format_map = {
                'csv': ExportFormat.CSV,
                'tsv': ExportFormat.TSV,
                'json': ExportFormat.JSON,
                'jsonl': ExportFormat.JSONL,
                'xlsx': ExportFormat.EXCEL,
                'xml': ExportFormat.XML,
            }
            format = format_map.get(ext, ExportFormat.CSV)

        result = self.export(data, format, options)

        if result.success and result.data:
            with open(file_path, 'wb') as f:
                f.write(result.data)
            result.file_path = file_path

        return result

    # ========================================================================
    # ASYNC EXPORT
    # ========================================================================

    async def export_async(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        format: ExportFormat = ExportFormat.CSV,
        options: Optional[ExportOptions] = None
    ) -> ExportResult:
        """Export data asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.export,
            data,
            format,
            options
        )

    # ========================================================================
    # BACKGROUND JOBS
    # ========================================================================

    async def create_job(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        format: ExportFormat = ExportFormat.CSV,
        options: Optional[ExportOptions] = None
    ) -> ExportJob:
        """Create a background export job."""
        job = ExportJob(
            id=str(uuid.uuid4()),
            format=format,
            options=options or ExportOptions(format=format)
        )

        with self._lock:
            self._jobs[job.id] = job

        # Start processing
        asyncio.create_task(self._process_job(job, data))

        return job

    async def _process_job(
        self,
        job: ExportJob,
        data: Union[List[Dict], Iterator[Dict]]
    ) -> None:
        """Process an export job."""
        job.status = ExportStatus.PROCESSING
        job.started_at = datetime.now()

        try:
            result = await self.export_async(data, job.format, job.options)
            job.result = result
            job.status = ExportStatus.COMPLETED

        except Exception as e:
            job.result = ExportResult(
                success=False,
                format=job.format,
                error=str(e)
            )
            job.status = ExportStatus.FAILED

        finally:
            job.completed_at = datetime.now()

    def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    def to_csv(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        **kwargs
    ) -> bytes:
        """Export to CSV."""
        result = self.export(data, ExportFormat.CSV, ExportOptions(**kwargs))
        return result.data or b''

    def to_json(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        **kwargs
    ) -> bytes:
        """Export to JSON."""
        result = self.export(data, ExportFormat.JSON, ExportOptions(**kwargs))
        return result.data or b''

    def to_excel(
        self,
        data: Union[List[Dict], Iterator[Dict]],
        **kwargs
    ) -> bytes:
        """Export to Excel."""
        result = self.export(data, ExportFormat.EXCEL, ExportOptions(**kwargs))
        return result.data or b''

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'supported_formats': [f.value for f in self._exporters.keys()],
            'jobs': len(self._jobs),
            'stats': dict(self._stats)
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

export_engine = ExportEngine()
