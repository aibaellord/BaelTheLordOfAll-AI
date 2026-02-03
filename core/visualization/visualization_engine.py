#!/usr/bin/env python3
"""
BAEL - Visualization Engine
Data visualization and charting for agents.

Features:
- Chart generation
- Data visualization
- Graph rendering
- Dashboard composition
- Visual analytics
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ChartType(Enum):
    """Types of charts."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    AREA = "area"
    HEATMAP = "heatmap"
    BOX = "box"


class ColorScheme(Enum):
    """Color schemes for visualization."""
    DEFAULT = "default"
    MONOCHROME = "monochrome"
    WARM = "warm"
    COOL = "cool"
    RAINBOW = "rainbow"
    CATEGORICAL = "categorical"


class ScaleType(Enum):
    """Types of scales."""
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    CATEGORICAL = "categorical"
    TIME = "time"


class LegendPosition(Enum):
    """Position of legend."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"


class AxisType(Enum):
    """Types of axes."""
    X = "x"
    Y = "y"
    Z = "z"


class RenderFormat(Enum):
    """Render output formats."""
    ASCII = "ascii"
    SVG = "svg"
    JSON = "json"
    MARKDOWN = "markdown"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataSeries:
    """A data series for visualization."""
    series_id: str = ""
    name: str = ""
    values: List[float] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    color: str = ""

    def __post_init__(self):
        if not self.series_id:
            self.series_id = str(uuid.uuid4())[:8]


@dataclass
class Axis:
    """An axis configuration."""
    axis_id: str = ""
    axis_type: AxisType = AxisType.X
    label: str = ""
    scale: ScaleType = ScaleType.LINEAR
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def __post_init__(self):
        if not self.axis_id:
            self.axis_id = str(uuid.uuid4())[:8]


@dataclass
class Chart:
    """A chart configuration."""
    chart_id: str = ""
    title: str = ""
    chart_type: ChartType = ChartType.LINE
    series: List[DataSeries] = field(default_factory=list)
    x_axis: Optional[Axis] = None
    y_axis: Optional[Axis] = None
    color_scheme: ColorScheme = ColorScheme.DEFAULT
    legend_position: LegendPosition = LegendPosition.RIGHT
    width: int = 80
    height: int = 20

    def __post_init__(self):
        if not self.chart_id:
            self.chart_id = str(uuid.uuid4())[:8]


@dataclass
class Dashboard:
    """A dashboard of charts."""
    dashboard_id: str = ""
    title: str = ""
    charts: List[Chart] = field(default_factory=list)
    layout: List[List[str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.dashboard_id:
            self.dashboard_id = str(uuid.uuid4())[:8]


@dataclass
class VisualizationConfig:
    """Visualization engine configuration."""
    default_width: int = 80
    default_height: int = 20
    default_color_scheme: ColorScheme = ColorScheme.DEFAULT
    default_format: RenderFormat = RenderFormat.ASCII


# =============================================================================
# DATA PROCESSOR
# =============================================================================

class DataProcessor:
    """Process data for visualization."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def normalize(
        self,
        values: List[float],
        min_val: float = 0.0,
        max_val: float = 1.0
    ) -> List[float]:
        """Normalize values to range."""
        if not values:
            return []

        data_min = min(values)
        data_max = max(values)

        if data_min == data_max:
            return [0.5] * len(values)

        return [
            min_val + (v - data_min) / (data_max - data_min) * (max_val - min_val)
            for v in values
        ]

    def compute_bins(
        self,
        values: List[float],
        num_bins: int = 10
    ) -> Tuple[List[float], List[int]]:
        """Compute histogram bins."""
        if not values:
            return [], []

        data_min = min(values)
        data_max = max(values)

        bin_width = (data_max - data_min) / num_bins if data_max != data_min else 1

        bins = [data_min + i * bin_width for i in range(num_bins + 1)]
        counts = [0] * num_bins

        for v in values:
            bin_idx = min(int((v - data_min) / bin_width), num_bins - 1) if bin_width > 0 else 0
            counts[bin_idx] += 1

        return bins, counts

    def compute_statistics(
        self,
        values: List[float]
    ) -> Dict[str, float]:
        """Compute basic statistics."""
        if not values:
            return {}

        n = len(values)
        mean = sum(values) / n

        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)

        return {
            "count": n,
            "mean": mean,
            "median": median,
            "std": std,
            "min": min(values),
            "max": max(values),
            "sum": sum(values)
        }

    def aggregate(
        self,
        values: List[float],
        window_size: int = 5
    ) -> List[float]:
        """Aggregate values with moving average."""
        if not values or window_size <= 0:
            return values

        result = []

        for i in range(len(values)):
            start = max(0, i - window_size + 1)
            window = values[start:i + 1]
            result.append(sum(window) / len(window))

        return result

    def interpolate(
        self,
        values: List[float],
        num_points: int
    ) -> List[float]:
        """Interpolate values to new resolution."""
        if not values or num_points <= 0:
            return []

        if len(values) == 1:
            return [values[0]] * num_points

        result = []

        for i in range(num_points):
            t = i / (num_points - 1) * (len(values) - 1)
            idx = int(t)
            frac = t - idx

            if idx >= len(values) - 1:
                result.append(values[-1])
            else:
                result.append(values[idx] * (1 - frac) + values[idx + 1] * frac)

        return result


# =============================================================================
# CHART BUILDER
# =============================================================================

class ChartBuilder:
    """Build charts from data."""

    def __init__(
        self,
        default_width: int = 80,
        default_height: int = 20
    ):
        self._charts: Dict[str, Chart] = {}
        self._default_width = default_width
        self._default_height = default_height

    def create_chart(
        self,
        title: str,
        chart_type: ChartType,
        width: Optional[int] = None,
        height: Optional[int] = None,
        color_scheme: ColorScheme = ColorScheme.DEFAULT
    ) -> Chart:
        """Create a chart."""
        chart = Chart(
            title=title,
            chart_type=chart_type,
            width=width or self._default_width,
            height=height or self._default_height,
            color_scheme=color_scheme
        )

        self._charts[chart.chart_id] = chart

        return chart

    def add_series(
        self,
        chart_id: str,
        name: str,
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> Optional[DataSeries]:
        """Add data series to chart."""
        chart = self._charts.get(chart_id)

        if not chart:
            return None

        series = DataSeries(
            name=name,
            values=values,
            labels=labels or [str(i) for i in range(len(values))]
        )

        chart.series.append(series)

        return series

    def set_x_axis(
        self,
        chart_id: str,
        label: str,
        scale: ScaleType = ScaleType.LINEAR,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """Set X axis configuration."""
        chart = self._charts.get(chart_id)

        if not chart:
            return False

        chart.x_axis = Axis(
            axis_type=AxisType.X,
            label=label,
            scale=scale,
            min_value=min_value,
            max_value=max_value
        )

        return True

    def set_y_axis(
        self,
        chart_id: str,
        label: str,
        scale: ScaleType = ScaleType.LINEAR,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """Set Y axis configuration."""
        chart = self._charts.get(chart_id)

        if not chart:
            return False

        chart.y_axis = Axis(
            axis_type=AxisType.Y,
            label=label,
            scale=scale,
            min_value=min_value,
            max_value=max_value
        )

        return True

    def set_legend(
        self,
        chart_id: str,
        position: LegendPosition
    ) -> bool:
        """Set legend position."""
        chart = self._charts.get(chart_id)

        if not chart:
            return False

        chart.legend_position = position

        return True

    def get_chart(self, chart_id: str) -> Optional[Chart]:
        """Get chart by ID."""
        return self._charts.get(chart_id)

    def delete_chart(self, chart_id: str) -> bool:
        """Delete a chart."""
        if chart_id in self._charts:
            del self._charts[chart_id]
            return True
        return False

    def count(self) -> int:
        """Count charts."""
        return len(self._charts)

    def all(self) -> List[Chart]:
        """Get all charts."""
        return list(self._charts.values())


# =============================================================================
# ASCII RENDERER
# =============================================================================

class ASCIIRenderer:
    """Render charts to ASCII art."""

    def __init__(self):
        self._symbols = ["█", "▓", "▒", "░", "▄", "▀", "●", "○"]
        self._bar_char = "█"
        self._line_chars = ["─", "│", "┌", "┐", "└", "┘"]

    def render_line_chart(self, chart: Chart) -> str:
        """Render line chart as ASCII."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        values = chart.series[0].values
        width = chart.width - 10
        height = chart.height - 4

        processor = DataProcessor()
        normalized = processor.normalize(values, 0, height - 1)

        if len(normalized) > width:
            normalized = processor.interpolate(normalized, width)

        grid = [[" " for _ in range(width)] for _ in range(height)]

        for x, y in enumerate(normalized):
            if x < width:
                row = height - 1 - int(y)
                if 0 <= row < height:
                    grid[row][x] = "●"

        lines = []
        lines.append(f"┌{'─' * width}┐ {chart.title}")

        for row in grid:
            lines.append(f"│{''.join(row)}│")

        lines.append(f"└{'─' * width}┘")

        return "\n".join(lines)

    def render_bar_chart(self, chart: Chart) -> str:
        """Render bar chart as ASCII."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        values = chart.series[0].values
        labels = chart.series[0].labels or [f"#{i}" for i in range(len(values))]

        max_val = max(values) if values else 1
        bar_width = chart.width - 15

        lines = []
        lines.append(chart.title)
        lines.append("-" * chart.width)

        for i, (label, value) in enumerate(zip(labels, values)):
            bar_len = int(value / max_val * bar_width) if max_val else 0
            bar = self._bar_char * bar_len
            lines.append(f"{label[:8]:>8} │{bar} {value:.1f}")

        lines.append("-" * chart.width)

        return "\n".join(lines)

    def render_pie_chart(self, chart: Chart) -> str:
        """Render pie chart as ASCII (simplified)."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        values = chart.series[0].values
        labels = chart.series[0].labels or [f"#{i}" for i in range(len(values))]

        total = sum(values)

        lines = []
        lines.append(chart.title)
        lines.append("-" * 40)

        for label, value in zip(labels, values):
            pct = value / total * 100 if total else 0
            bar_len = int(pct / 5)
            bar = "█" * bar_len
            lines.append(f"{label[:12]:>12} │{bar} {pct:.1f}%")

        lines.append("-" * 40)
        lines.append(f"{'Total':>12} │ {total:.1f}")

        return "\n".join(lines)

    def render_scatter_chart(self, chart: Chart) -> str:
        """Render scatter chart as ASCII."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        values = chart.series[0].values
        width = chart.width - 10
        height = chart.height - 4

        processor = DataProcessor()
        normalized = processor.normalize(values, 0, height - 1)

        grid = [[" " for _ in range(width)] for _ in range(height)]

        for i, y in enumerate(normalized):
            x = int(i / len(normalized) * (width - 1))
            row = height - 1 - int(y)
            if 0 <= row < height and 0 <= x < width:
                grid[row][x] = "•"

        lines = []
        lines.append(f"┌{'─' * width}┐ {chart.title}")

        for row in grid:
            lines.append(f"│{''.join(row)}│")

        lines.append(f"└{'─' * width}┘")

        return "\n".join(lines)

    def render_histogram(self, chart: Chart) -> str:
        """Render histogram as ASCII."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        values = chart.series[0].values
        processor = DataProcessor()

        bins, counts = processor.compute_bins(values, 10)

        max_count = max(counts) if counts else 1
        bar_width = chart.width - 20

        lines = []
        lines.append(chart.title)
        lines.append("-" * chart.width)

        for i, count in enumerate(counts):
            bin_label = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
            bar_len = int(count / max_count * bar_width) if max_count else 0
            bar = "█" * bar_len
            lines.append(f"{bin_label:>10} │{bar} {count}")

        lines.append("-" * chart.width)

        return "\n".join(lines)

    def render(self, chart: Chart) -> str:
        """Render chart based on type."""
        renderers = {
            ChartType.LINE: self.render_line_chart,
            ChartType.BAR: self.render_bar_chart,
            ChartType.PIE: self.render_pie_chart,
            ChartType.SCATTER: self.render_scatter_chart,
            ChartType.HISTOGRAM: self.render_histogram,
        }

        renderer = renderers.get(chart.chart_type, self.render_bar_chart)

        return renderer(chart)


# =============================================================================
# DASHBOARD MANAGER
# =============================================================================

class DashboardManager:
    """Manage visualization dashboards."""

    def __init__(self):
        self._dashboards: Dict[str, Dashboard] = {}

    def create_dashboard(self, title: str) -> Dashboard:
        """Create a dashboard."""
        dashboard = Dashboard(title=title)
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    def add_chart(
        self,
        dashboard_id: str,
        chart: Chart
    ) -> bool:
        """Add chart to dashboard."""
        dashboard = self._dashboards.get(dashboard_id)

        if not dashboard:
            return False

        dashboard.charts.append(chart)

        return True

    def set_layout(
        self,
        dashboard_id: str,
        layout: List[List[str]]
    ) -> bool:
        """Set dashboard layout."""
        dashboard = self._dashboards.get(dashboard_id)

        if not dashboard:
            return False

        dashboard.layout = layout

        return True

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False

    def count(self) -> int:
        """Count dashboards."""
        return len(self._dashboards)

    def all(self) -> List[Dashboard]:
        """Get all dashboards."""
        return list(self._dashboards.values())


# =============================================================================
# VISUALIZATION ENGINE
# =============================================================================

class VisualizationEngine:
    """
    Visualization Engine for BAEL.

    Data visualization and charting.
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self._config = config or VisualizationConfig()

        self._data_processor = DataProcessor()
        self._chart_builder = ChartBuilder(
            self._config.default_width,
            self._config.default_height
        )
        self._ascii_renderer = ASCIIRenderer()
        self._dashboard_manager = DashboardManager()

    # ----- Data Operations -----

    def normalize(
        self,
        values: List[float],
        min_val: float = 0.0,
        max_val: float = 1.0
    ) -> List[float]:
        """Normalize values."""
        return self._data_processor.normalize(values, min_val, max_val)

    def compute_statistics(
        self,
        values: List[float]
    ) -> Dict[str, float]:
        """Compute statistics."""
        return self._data_processor.compute_statistics(values)

    def aggregate(
        self,
        values: List[float],
        window_size: int = 5
    ) -> List[float]:
        """Aggregate values with moving average."""
        return self._data_processor.aggregate(values, window_size)

    # ----- Chart Operations -----

    def create_chart(
        self,
        title: str,
        chart_type: ChartType,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Chart:
        """Create a chart."""
        return self._chart_builder.create_chart(
            title=title,
            chart_type=chart_type,
            width=width,
            height=height,
            color_scheme=self._config.default_color_scheme
        )

    def add_series(
        self,
        chart_id: str,
        name: str,
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> Optional[DataSeries]:
        """Add data series to chart."""
        return self._chart_builder.add_series(chart_id, name, values, labels)

    def set_x_axis(
        self,
        chart_id: str,
        label: str,
        scale: ScaleType = ScaleType.LINEAR
    ) -> bool:
        """Set X axis."""
        return self._chart_builder.set_x_axis(chart_id, label, scale)

    def set_y_axis(
        self,
        chart_id: str,
        label: str,
        scale: ScaleType = ScaleType.LINEAR
    ) -> bool:
        """Set Y axis."""
        return self._chart_builder.set_y_axis(chart_id, label, scale)

    def get_chart(self, chart_id: str) -> Optional[Chart]:
        """Get chart by ID."""
        return self._chart_builder.get_chart(chart_id)

    # ----- Quick Chart Builders -----

    def line_chart(
        self,
        title: str,
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> Chart:
        """Create a quick line chart."""
        chart = self.create_chart(title, ChartType.LINE)
        self.add_series(chart.chart_id, "Data", values, labels)
        return chart

    def bar_chart(
        self,
        title: str,
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> Chart:
        """Create a quick bar chart."""
        chart = self.create_chart(title, ChartType.BAR)
        self.add_series(chart.chart_id, "Data", values, labels)
        return chart

    def pie_chart(
        self,
        title: str,
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> Chart:
        """Create a quick pie chart."""
        chart = self.create_chart(title, ChartType.PIE)
        self.add_series(chart.chart_id, "Data", values, labels)
        return chart

    def scatter_chart(
        self,
        title: str,
        values: List[float]
    ) -> Chart:
        """Create a quick scatter chart."""
        chart = self.create_chart(title, ChartType.SCATTER)
        self.add_series(chart.chart_id, "Data", values)
        return chart

    def histogram(
        self,
        title: str,
        values: List[float]
    ) -> Chart:
        """Create a quick histogram."""
        chart = self.create_chart(title, ChartType.HISTOGRAM)
        self.add_series(chart.chart_id, "Data", values)
        return chart

    # ----- Rendering Operations -----

    def render(
        self,
        chart: Chart,
        format: Optional[RenderFormat] = None
    ) -> str:
        """Render chart to string."""
        format = format or self._config.default_format

        if format == RenderFormat.ASCII:
            return self._ascii_renderer.render(chart)
        elif format == RenderFormat.JSON:
            return self._render_json(chart)
        elif format == RenderFormat.MARKDOWN:
            return self._render_markdown(chart)
        else:
            return self._ascii_renderer.render(chart)

    def _render_json(self, chart: Chart) -> str:
        """Render chart as JSON."""
        data = {
            "title": chart.title,
            "type": chart.chart_type.value,
            "series": [
                {
                    "name": s.name,
                    "values": s.values,
                    "labels": s.labels
                }
                for s in chart.series
            ]
        }

        return json.dumps(data, indent=2)

    def _render_markdown(self, chart: Chart) -> str:
        """Render chart as Markdown table."""
        if not chart.series or not chart.series[0].values:
            return "No data"

        series = chart.series[0]

        lines = []
        lines.append(f"## {chart.title}")
        lines.append("")
        lines.append("| Label | Value |")
        lines.append("|-------|-------|")

        for label, value in zip(series.labels, series.values):
            lines.append(f"| {label} | {value:.2f} |")

        return "\n".join(lines)

    # ----- Dashboard Operations -----

    def create_dashboard(self, title: str) -> Dashboard:
        """Create a dashboard."""
        return self._dashboard_manager.create_dashboard(title)

    def add_chart_to_dashboard(
        self,
        dashboard_id: str,
        chart: Chart
    ) -> bool:
        """Add chart to dashboard."""
        return self._dashboard_manager.add_chart(dashboard_id, chart)

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard by ID."""
        return self._dashboard_manager.get_dashboard(dashboard_id)

    def render_dashboard(self, dashboard: Dashboard) -> str:
        """Render entire dashboard."""
        lines = []
        lines.append("=" * 80)
        lines.append(f" {dashboard.title}")
        lines.append("=" * 80)
        lines.append("")

        for chart in dashboard.charts:
            lines.append(self.render(chart))
            lines.append("")

        return "\n".join(lines)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "charts": self._chart_builder.count(),
            "dashboards": self._dashboard_manager.count()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Visualization Engine."""
    print("=" * 70)
    print("BAEL - VISUALIZATION ENGINE DEMO")
    print("Data Visualization and Charting")
    print("=" * 70)
    print()

    engine = VisualizationEngine()

    # 1. Create Line Chart
    print("1. LINE CHART:")
    print("-" * 40)

    values = [10, 25, 15, 30, 45, 35, 50, 40, 55, 60]
    line = engine.line_chart("Sales Trend", values)

    print(engine.render(line))
    print()

    # 2. Create Bar Chart
    print("2. BAR CHART:")
    print("-" * 40)

    bar_values = [45, 30, 60, 25, 50]
    bar_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    bar = engine.bar_chart("Weekly Activity", bar_values, bar_labels)

    print(engine.render(bar))
    print()

    # 3. Create Pie Chart
    print("3. PIE CHART:")
    print("-" * 40)

    pie_values = [35, 25, 20, 15, 5]
    pie_labels = ["Product A", "Product B", "Product C", "Product D", "Other"]
    pie = engine.pie_chart("Market Share", pie_values, pie_labels)

    print(engine.render(pie))
    print()

    # 4. Create Scatter Chart
    print("4. SCATTER CHART:")
    print("-" * 40)

    scatter_values = [random.random() * 100 for _ in range(20)]
    scatter = engine.scatter_chart("Data Points", scatter_values)

    print(engine.render(scatter))
    print()

    # 5. Create Histogram
    print("5. HISTOGRAM:")
    print("-" * 40)

    hist_values = [random.gauss(50, 15) for _ in range(100)]
    hist = engine.histogram("Distribution", hist_values)

    print(engine.render(hist))
    print()

    # 6. Compute Statistics
    print("6. COMPUTE STATISTICS:")
    print("-" * 40)

    stats = engine.compute_statistics(values)

    for key, value in stats.items():
        print(f"   {key}: {value:.2f}")
    print()

    # 7. Normalize Data
    print("7. NORMALIZE DATA:")
    print("-" * 40)

    normalized = engine.normalize(values, 0, 1)

    print(f"   Original: {values[:5]}...")
    print(f"   Normalized: {[round(v, 2) for v in normalized[:5]]}...")
    print()

    # 8. Aggregate Data
    print("8. AGGREGATE DATA:")
    print("-" * 40)

    aggregated = engine.aggregate(values, window_size=3)

    print(f"   Original: {values}")
    print(f"   Aggregated: {[round(v, 2) for v in aggregated]}")
    print()

    # 9. Create Custom Chart
    print("9. CUSTOM CHART:")
    print("-" * 40)

    custom = engine.create_chart("Custom Analysis", ChartType.LINE, width=60, height=15)
    engine.add_series(custom.chart_id, "Series A", [10, 20, 15, 25, 30])
    engine.set_x_axis(custom.chart_id, "Time")
    engine.set_y_axis(custom.chart_id, "Value")

    print(engine.render(custom))
    print()

    # 10. Render as JSON
    print("10. RENDER AS JSON:")
    print("-" * 40)

    json_output = engine.render(bar, RenderFormat.JSON)
    print(json_output[:200] + "...")
    print()

    # 11. Render as Markdown
    print("11. RENDER AS MARKDOWN:")
    print("-" * 40)

    md_output = engine.render(bar, RenderFormat.MARKDOWN)
    print(md_output)
    print()

    # 12. Create Dashboard
    print("12. CREATE DASHBOARD:")
    print("-" * 40)

    dashboard = engine.create_dashboard("Analytics Dashboard")

    chart1 = engine.bar_chart("Revenue", [100, 150, 120, 180], ["Q1", "Q2", "Q3", "Q4"])
    chart2 = engine.line_chart("Users", [500, 600, 750, 900, 1100])

    engine.add_chart_to_dashboard(dashboard.dashboard_id, chart1)
    engine.add_chart_to_dashboard(dashboard.dashboard_id, chart2)

    print(f"   Dashboard: {dashboard.title}")
    print(f"   Charts: {len(dashboard.charts)}")
    print()

    # 13. Render Dashboard
    print("13. RENDER DASHBOARD:")
    print("-" * 40)

    dashboard_output = engine.render_dashboard(dashboard)
    print(dashboard_output)
    print()

    # 14. Get Chart
    print("14. GET CHART:")
    print("-" * 40)

    retrieved = engine.get_chart(bar.chart_id)
    if retrieved:
        print(f"   Chart: {retrieved.title}")
        print(f"   Type: {retrieved.chart_type.value}")
        print(f"   Series count: {len(retrieved.series)}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Visualization Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
