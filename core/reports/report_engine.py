#!/usr/bin/env python3
"""
BAEL - Report Engine
Comprehensive report generation system.

Features:
- Multiple output formats
- Template-based reports
- Data aggregation
- Charts and visualizations
- Scheduling
- Email delivery
- Parameterized reports
- Caching
- Async generation
- Export capabilities
"""

import asyncio
import csv
import io
import json
import logging
import statistics
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ReportFormat(Enum):
    """Output formats for reports."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"
    TEXT = "text"
    XML = "xml"


class ReportStatus(Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class AggregationType(Enum):
    """Types of data aggregation."""
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    MODE = "mode"
    STD_DEV = "std_dev"


class ChartType(Enum):
    """Types of charts."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    TABLE = "table"
    GAUGE = "gauge"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ReportParameter:
    """Parameter for a report."""
    name: str
    param_type: str = "string"  # string, int, float, date, bool, list
    required: bool = True
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None


@dataclass
class DataColumn:
    """Column definition for report data."""
    name: str
    label: str = ""
    data_type: str = "string"
    format_string: Optional[str] = None
    aggregation: Optional[AggregationType] = None

    def __post_init__(self):
        if not self.label:
            self.label = self.name.replace("_", " ").title()


@dataclass
class ChartConfig:
    """Configuration for a chart."""
    chart_type: ChartType
    title: str = ""
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    series: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    width: int = 600
    height: int = 400


@dataclass
class ReportSection:
    """A section of a report."""
    title: str
    content_type: str = "data"  # data, text, chart, summary
    columns: List[DataColumn] = field(default_factory=list)
    data: List[Dict[str, Any]] = field(default_factory=list)
    text: str = ""
    chart: Optional[ChartConfig] = None
    order: int = 0


@dataclass
class ReportDefinition:
    """Definition of a report."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parameters: List[ReportParameter] = field(default_factory=list)
    sections: List[ReportSection] = field(default_factory=list)
    data_source: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """A generated report."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    definition_id: str = ""
    status: ReportStatus = ReportStatus.PENDING
    format: ReportFormat = ReportFormat.JSON
    parameters: Dict[str, Any] = field(default_factory=dict)
    content: str = ""
    generated_at: Optional[datetime] = None
    generation_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# DATA AGGREGATION
# =============================================================================

class DataAggregator:
    """Aggregate data for reports."""

    @staticmethod
    def aggregate(
        data: List[Dict[str, Any]],
        column: str,
        aggregation: AggregationType
    ) -> Any:
        """Perform aggregation on data."""
        values = [row.get(column) for row in data if row.get(column) is not None]

        if not values:
            return None

        # Filter numeric values for numeric aggregations
        numeric = [v for v in values if isinstance(v, (int, float))]

        if aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.SUM:
            return sum(numeric) if numeric else 0
        elif aggregation == AggregationType.AVERAGE:
            return statistics.mean(numeric) if numeric else 0
        elif aggregation == AggregationType.MIN:
            return min(numeric) if numeric else None
        elif aggregation == AggregationType.MAX:
            return max(numeric) if numeric else None
        elif aggregation == AggregationType.MEDIAN:
            return statistics.median(numeric) if numeric else None
        elif aggregation == AggregationType.MODE:
            try:
                return statistics.mode(values)
            except statistics.StatisticsError:
                return values[0] if values else None
        elif aggregation == AggregationType.STD_DEV:
            return statistics.stdev(numeric) if len(numeric) > 1 else 0

        return None

    @staticmethod
    def group_by(
        data: List[Dict[str, Any]],
        key: str,
        aggregations: Dict[str, AggregationType]
    ) -> List[Dict[str, Any]]:
        """Group data and apply aggregations."""
        groups: Dict[Any, List[Dict]] = {}

        for row in data:
            group_key = row.get(key)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)

        result = []
        for group_key, group_data in groups.items():
            row = {key: group_key}

            for column, agg in aggregations.items():
                row[f"{column}_{agg.value}"] = DataAggregator.aggregate(
                    group_data, column, agg
                )

            result.append(row)

        return result


# =============================================================================
# FORMATTERS
# =============================================================================

class ReportFormatter(ABC):
    """Abstract report formatter."""

    @abstractmethod
    def format(
        self,
        definition: ReportDefinition,
        data: List[ReportSection]
    ) -> str:
        """Format report to string."""
        pass


class JSONFormatter(ReportFormatter):
    """JSON report formatter."""

    def format(
        self,
        definition: ReportDefinition,
        sections: List[ReportSection]
    ) -> str:
        report = {
            "name": definition.name,
            "description": definition.description,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": []
        }

        for section in sections:
            section_data = {
                "title": section.title,
                "type": section.content_type
            }

            if section.content_type == "data":
                section_data["columns"] = [
                    {"name": c.name, "label": c.label}
                    for c in section.columns
                ]
                section_data["data"] = section.data
            elif section.content_type == "text":
                section_data["text"] = section.text

            report["sections"].append(section_data)

        return json.dumps(report, indent=2, default=str)


class CSVFormatter(ReportFormatter):
    """CSV report formatter."""

    def format(
        self,
        definition: ReportDefinition,
        sections: List[ReportSection]
    ) -> str:
        output = io.StringIO()

        for section in sections:
            if section.content_type != "data" or not section.data:
                continue

            # Write section header
            output.write(f"# {section.title}\n")

            # Get columns
            if section.columns:
                columns = [c.name for c in section.columns]
            else:
                columns = list(section.data[0].keys()) if section.data else []

            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()

            for row in section.data:
                writer.writerow({k: row.get(k, "") for k in columns})

            output.write("\n")

        return output.getvalue()


class HTMLFormatter(ReportFormatter):
    """HTML report formatter."""

    def format(
        self,
        definition: ReportDefinition,
        sections: List[ReportSection]
    ) -> str:
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{definition.name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 1px solid #ccc; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            "tr:nth-child(even) { background-color: #f2f2f2; }",
            ".summary { background: #f9f9f9; padding: 15px; border-radius: 5px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{definition.name}</h1>",
            f"<p>{definition.description}</p>",
            f"<p><em>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</em></p>"
        ]

        for section in sections:
            html.append(f"<h2>{section.title}</h2>")

            if section.content_type == "data" and section.data:
                html.append("<table>")

                # Headers
                if section.columns:
                    cols = section.columns
                else:
                    cols = [DataColumn(name=k) for k in section.data[0].keys()]

                html.append("<tr>")
                for col in cols:
                    html.append(f"<th>{col.label}</th>")
                html.append("</tr>")

                # Data rows
                for row in section.data:
                    html.append("<tr>")
                    for col in cols:
                        value = row.get(col.name, "")
                        if col.format_string and value is not None:
                            try:
                                value = col.format_string.format(value)
                            except:
                                pass
                        html.append(f"<td>{value}</td>")
                    html.append("</tr>")

                html.append("</table>")

            elif section.content_type == "text":
                html.append(f"<p>{section.text}</p>")

            elif section.content_type == "summary":
                html.append("<div class='summary'>")
                html.append(f"<p>{section.text}</p>")
                html.append("</div>")

        html.extend(["</body>", "</html>"])

        return "\n".join(html)


class MarkdownFormatter(ReportFormatter):
    """Markdown report formatter."""

    def format(
        self,
        definition: ReportDefinition,
        sections: List[ReportSection]
    ) -> str:
        md = [
            f"# {definition.name}",
            "",
            f"*{definition.description}*",
            "",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]

        for section in sections:
            md.append(f"## {section.title}")
            md.append("")

            if section.content_type == "data" and section.data:
                # Get columns
                if section.columns:
                    cols = section.columns
                else:
                    cols = [DataColumn(name=k) for k in section.data[0].keys()]

                # Header row
                header = "| " + " | ".join(c.label for c in cols) + " |"
                separator = "| " + " | ".join("---" for _ in cols) + " |"

                md.append(header)
                md.append(separator)

                # Data rows
                for row in section.data:
                    values = []
                    for col in cols:
                        v = row.get(col.name, "")
                        values.append(str(v))
                    md.append("| " + " | ".join(values) + " |")

                md.append("")

            elif section.content_type in ("text", "summary"):
                md.append(section.text)
                md.append("")

        return "\n".join(md)


class TextFormatter(ReportFormatter):
    """Plain text report formatter."""

    def format(
        self,
        definition: ReportDefinition,
        sections: List[ReportSection]
    ) -> str:
        lines = [
            "=" * 60,
            definition.name.upper(),
            "=" * 60,
            "",
            definition.description,
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        for section in sections:
            lines.append("-" * 40)
            lines.append(section.title)
            lines.append("-" * 40)

            if section.content_type == "data" and section.data:
                # Get column widths
                if section.columns:
                    cols = section.columns
                else:
                    cols = [DataColumn(name=k) for k in section.data[0].keys()]

                widths = {}
                for col in cols:
                    widths[col.name] = max(
                        len(col.label),
                        max(len(str(row.get(col.name, ""))) for row in section.data)
                    )

                # Header
                header = "  ".join(col.label.ljust(widths[col.name]) for col in cols)
                lines.append(header)
                lines.append("-" * len(header))

                # Data
                for row in section.data:
                    line = "  ".join(
                        str(row.get(col.name, "")).ljust(widths[col.name])
                        for col in cols
                    )
                    lines.append(line)

            elif section.content_type in ("text", "summary"):
                lines.append(section.text)

            lines.append("")

        return "\n".join(lines)


# =============================================================================
# REPORT ENGINE
# =============================================================================

class ReportEngine:
    """
    Report Engine for BAEL.

    Generates comprehensive reports in multiple formats.
    """

    FORMATTERS: Dict[ReportFormat, Type[ReportFormatter]] = {
        ReportFormat.JSON: JSONFormatter,
        ReportFormat.CSV: CSVFormatter,
        ReportFormat.HTML: HTMLFormatter,
        ReportFormat.MARKDOWN: MarkdownFormatter,
        ReportFormat.TEXT: TextFormatter
    }

    def __init__(self):
        self._definitions: Dict[str, ReportDefinition] = {}
        self._generated: Dict[str, GeneratedReport] = {}
        self._cache: Dict[str, Tuple[GeneratedReport, datetime]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._listeners: List[Callable[[GeneratedReport], Awaitable[None]]] = []

    # -------------------------------------------------------------------------
    # DEFINITION MANAGEMENT
    # -------------------------------------------------------------------------

    def register(self, definition: ReportDefinition) -> None:
        """Register a report definition."""
        self._definitions[definition.id] = definition

    def create_definition(
        self,
        name: str,
        description: str = "",
        parameters: Optional[List[ReportParameter]] = None,
        data_source: Optional[Callable] = None
    ) -> ReportDefinition:
        """Create and register a report definition."""
        definition = ReportDefinition(
            name=name,
            description=description,
            parameters=parameters or [],
            data_source=data_source
        )

        self.register(definition)
        return definition

    def get_definition(self, definition_id: str) -> Optional[ReportDefinition]:
        """Get definition by ID."""
        return self._definitions.get(definition_id)

    def list_definitions(self) -> List[Dict[str, Any]]:
        """List all registered definitions."""
        return [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "parameters": [p.name for p in d.parameters]
            }
            for d in self._definitions.values()
        ]

    # -------------------------------------------------------------------------
    # REPORT GENERATION
    # -------------------------------------------------------------------------

    async def generate(
        self,
        definition_id: str,
        format: ReportFormat = ReportFormat.JSON,
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> GeneratedReport:
        """Generate a report."""
        definition = self._definitions.get(definition_id)
        if not definition:
            raise ValueError(f"Definition not found: {definition_id}")

        params = parameters or {}

        # Check cache
        cache_key = f"{definition_id}:{format.value}:{hash(frozenset(params.items()))}"

        if use_cache and cache_key in self._cache:
            cached, cached_at = self._cache[cache_key]
            if (datetime.utcnow() - cached_at).total_seconds() < self._cache_ttl:
                cached.status = ReportStatus.CACHED
                return cached

        # Validate parameters
        self._validate_parameters(definition, params)

        # Create report record
        report = GeneratedReport(
            definition_id=definition_id,
            format=format,
            parameters=params,
            status=ReportStatus.GENERATING
        )

        start_time = datetime.utcnow()

        try:
            # Get data from source
            if definition.data_source:
                if asyncio.iscoroutinefunction(definition.data_source):
                    data = await definition.data_source(params)
                else:
                    data = definition.data_source(params)

                # Convert to sections if needed
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    section = ReportSection(
                        title="Data",
                        content_type="data",
                        data=data
                    )
                    definition.sections = [section]

            # Format report
            formatter = self.FORMATTERS.get(format, JSONFormatter)()
            report.content = formatter.format(definition, definition.sections)

            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.utcnow()
            report.generation_time = (datetime.utcnow() - start_time).total_seconds()

            # Cache
            self._cache[cache_key] = (report, datetime.utcnow())

        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error = str(e)
            logger.exception(f"Report generation failed: {e}")

        self._generated[report.id] = report

        # Notify listeners
        for listener in self._listeners:
            try:
                await listener(report)
            except Exception as e:
                logger.error(f"Listener error: {e}")

        return report

    def _validate_parameters(
        self,
        definition: ReportDefinition,
        params: Dict[str, Any]
    ) -> None:
        """Validate report parameters."""
        for param in definition.parameters:
            if param.required and param.name not in params:
                if param.default is None:
                    raise ValueError(f"Required parameter missing: {param.name}")
                params[param.name] = param.default

            if param.choices and param.name in params:
                if params[param.name] not in param.choices:
                    raise ValueError(
                        f"Invalid value for {param.name}: {params[param.name]}"
                    )

    # -------------------------------------------------------------------------
    # REPORT RETRIEVAL
    # -------------------------------------------------------------------------

    def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """Get generated report by ID."""
        return self._generated.get(report_id)

    def list_reports(
        self,
        definition_id: Optional[str] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 100
    ) -> List[GeneratedReport]:
        """List generated reports."""
        reports = list(self._generated.values())

        if definition_id:
            reports = [r for r in reports if r.definition_id == definition_id]

        if status:
            reports = [r for r in reports if r.status == status]

        reports.sort(key=lambda r: r.generated_at or datetime.min, reverse=True)

        return reports[:limit]

    # -------------------------------------------------------------------------
    # QUICK REPORTS
    # -------------------------------------------------------------------------

    async def quick_table_report(
        self,
        title: str,
        data: List[Dict[str, Any]],
        format: ReportFormat = ReportFormat.HTML
    ) -> str:
        """Generate a quick table report from data."""
        definition = ReportDefinition(
            name=title,
            sections=[
                ReportSection(
                    title=title,
                    content_type="data",
                    data=data
                )
            ]
        )

        formatter = self.FORMATTERS.get(format, HTMLFormatter)()
        return formatter.format(definition, definition.sections)

    async def quick_summary_report(
        self,
        title: str,
        data: List[Dict[str, Any]],
        group_by: str,
        aggregations: Dict[str, AggregationType],
        format: ReportFormat = ReportFormat.HTML
    ) -> str:
        """Generate a quick summary report with aggregations."""
        grouped = DataAggregator.group_by(data, group_by, aggregations)

        definition = ReportDefinition(
            name=title,
            sections=[
                ReportSection(
                    title="Summary",
                    content_type="data",
                    data=grouped
                )
            ]
        )

        formatter = self.FORMATTERS.get(format, HTMLFormatter)()
        return formatter.format(definition, definition.sections)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def add_listener(
        self,
        callback: Callable[[GeneratedReport], Awaitable[None]]
    ) -> None:
        """Add report generation listener."""
        self._listeners.append(callback)

    def clear_cache(self) -> None:
        """Clear report cache."""
        self._cache.clear()

    def set_cache_ttl(self, seconds: int) -> None:
        """Set cache TTL in seconds."""
        self._cache_ttl = seconds


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Report Engine."""
    print("=" * 70)
    print("BAEL - REPORT ENGINE DEMO")
    print("Comprehensive Report Generation")
    print("=" * 70)
    print()

    engine = ReportEngine()

    # Sample data
    sales_data = [
        {"product": "Widget A", "category": "Electronics", "quantity": 100, "revenue": 1500.00},
        {"product": "Widget B", "category": "Electronics", "quantity": 75, "revenue": 1125.00},
        {"product": "Gadget X", "category": "Accessories", "quantity": 200, "revenue": 600.00},
        {"product": "Gadget Y", "category": "Accessories", "quantity": 150, "revenue": 450.00},
        {"product": "Device Z", "category": "Electronics", "quantity": 50, "revenue": 2500.00}
    ]

    # 1. Create Report Definition
    print("1. CREATE REPORT DEFINITION:")
    print("-" * 40)

    def get_sales_data(params):
        if params.get("category"):
            return [d for d in sales_data if d["category"] == params["category"]]
        return sales_data

    definition = engine.create_definition(
        name="Sales Report",
        description="Comprehensive sales analysis report",
        parameters=[
            ReportParameter(
                name="category",
                required=False,
                description="Filter by category"
            )
        ],
        data_source=get_sales_data
    )

    # Add sections
    definition.sections = [
        ReportSection(
            title="Sales Data",
            content_type="data",
            columns=[
                DataColumn(name="product", label="Product Name"),
                DataColumn(name="category", label="Category"),
                DataColumn(name="quantity", label="Qty"),
                DataColumn(name="revenue", label="Revenue", format_string="${:.2f}")
            ],
            data=sales_data
        ),
        ReportSection(
            title="Summary",
            content_type="summary",
            text="This report shows sales performance across all product categories."
        )
    ]

    print(f"   Created: {definition.name}")
    print(f"   ID: {definition.id[:8]}...")
    print()

    # 2. Generate JSON Report
    print("2. GENERATE JSON REPORT:")
    print("-" * 40)

    report = await engine.generate(definition.id, ReportFormat.JSON)

    print(f"   Status: {report.status.value}")
    print(f"   Generation time: {report.generation_time:.4f}s")
    print(f"   Content preview:")
    print(f"   {report.content[:200]}...")
    print()

    # 3. Generate HTML Report
    print("3. GENERATE HTML REPORT:")
    print("-" * 40)

    report = await engine.generate(definition.id, ReportFormat.HTML)

    print(f"   Status: {report.status.value}")
    print(f"   Content length: {len(report.content)} chars")
    print(f"   Preview:")
    lines = report.content.split("\n")[:5]
    for line in lines:
        print(f"   {line[:60]}...")
    print()

    # 4. Generate Markdown Report
    print("4. GENERATE MARKDOWN REPORT:")
    print("-" * 40)

    report = await engine.generate(definition.id, ReportFormat.MARKDOWN)

    print(f"   Status: {report.status.value}")
    print(f"   Content preview:")
    print(f"   {report.content[:300]}...")
    print()

    # 5. Generate CSV Report
    print("5. GENERATE CSV REPORT:")
    print("-" * 40)

    report = await engine.generate(definition.id, ReportFormat.CSV)

    print(f"   Status: {report.status.value}")
    print(f"   Content preview:")
    print(f"   {report.content[:200]}...")
    print()

    # 6. Generate Text Report
    print("6. GENERATE TEXT REPORT:")
    print("-" * 40)

    report = await engine.generate(definition.id, ReportFormat.TEXT)

    print(f"   Status: {report.status.value}")
    print(f"   Content preview:")
    for line in report.content.split("\n")[:8]:
        print(f"   {line}")
    print()

    # 7. Report with Parameters
    print("7. REPORT WITH PARAMETERS:")
    print("-" * 40)

    report = await engine.generate(
        definition.id,
        ReportFormat.JSON,
        parameters={"category": "Electronics"}
    )

    data = json.loads(report.content)
    print(f"   Category filter: Electronics")
    print(f"   Rows returned: {len(data['sections'][0]['data'])}")
    print()

    # 8. Cached Report
    print("8. CACHED REPORT:")
    print("-" * 40)

    report1 = await engine.generate(definition.id, ReportFormat.JSON)
    report2 = await engine.generate(definition.id, ReportFormat.JSON)

    print(f"   First request: {report1.status.value}")
    print(f"   Second request: {report2.status.value}")
    print()

    # 9. Data Aggregation
    print("9. DATA AGGREGATION:")
    print("-" * 40)

    aggregated = DataAggregator.group_by(
        sales_data,
        "category",
        {
            "quantity": AggregationType.SUM,
            "revenue": AggregationType.SUM
        }
    )

    for row in aggregated:
        print(f"   {row['category']}: qty={row['quantity_sum']}, revenue=${row['revenue_sum']:.2f}")
    print()

    # 10. Quick Table Report
    print("10. QUICK TABLE REPORT:")
    print("-" * 40)

    quick_html = await engine.quick_table_report(
        "Quick Sales",
        sales_data[:3],
        ReportFormat.MARKDOWN
    )

    print(f"   Generated quick report:")
    for line in quick_html.split("\n")[:8]:
        print(f"   {line}")
    print()

    # 11. Quick Summary Report
    print("11. QUICK SUMMARY REPORT:")
    print("-" * 40)

    summary = await engine.quick_summary_report(
        "Category Summary",
        sales_data,
        "category",
        {"revenue": AggregationType.SUM, "quantity": AggregationType.AVERAGE},
        ReportFormat.TEXT
    )

    for line in summary.split("\n")[:10]:
        print(f"   {line}")
    print()

    # 12. List Reports
    print("12. LIST GENERATED REPORTS:")
    print("-" * 40)

    reports = engine.list_reports(limit=5)

    for r in reports:
        print(f"   [{r.format.value}] {r.status.value} - {r.id[:8]}...")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Report Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
