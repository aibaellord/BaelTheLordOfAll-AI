"""
BAEL Dashboard Engine
======================

Dynamic dashboard creation and visualization.
Creates real-time monitoring dashboards.

Features:
- Dashboard composition
- Multiple chart types
- Real-time updates
- Layout management
- Export capabilities
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Types of charts."""
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    PIE = "pie"
    GAUGE = "gauge"
    STAT = "stat"
    TABLE = "table"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"


class WidgetSize(Enum):
    """Widget sizes."""
    SMALL = "small"       # 1/4 width
    MEDIUM = "medium"     # 1/2 width
    LARGE = "large"       # 3/4 width
    FULL = "full"         # Full width


@dataclass
class DataQuery:
    """Query for fetching data."""
    metric_name: str
    labels: Dict[str, str] = field(default_factory=dict)

    # Time range
    range_seconds: int = 3600  # 1 hour default
    step_seconds: int = 60    # 1 minute resolution

    # Aggregation
    aggregation: str = "avg"  # avg, sum, min, max, count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric_name,
            "labels": self.labels,
            "range": self.range_seconds,
            "step": self.step_seconds,
            "aggregation": self.aggregation,
        }


@dataclass
class ChartOptions:
    """Options for charts."""
    # Title
    title: str = ""
    subtitle: str = ""

    # Axes
    x_axis_label: str = ""
    y_axis_label: str = ""

    # Formatting
    unit: str = ""
    decimals: int = 2

    # Thresholds
    thresholds: List[Tuple[float, str]] = field(default_factory=list)  # (value, color)

    # Colors
    colors: List[str] = field(default_factory=list)

    # Legend
    show_legend: bool = True
    legend_position: str = "bottom"

    # Other
    stacked: bool = False
    fill: bool = False


@dataclass
class Widget:
    """A dashboard widget."""
    id: str
    title: str
    chart_type: ChartType = ChartType.LINE

    # Data
    queries: List[DataQuery] = field(default_factory=list)

    # Display
    options: ChartOptions = field(default_factory=ChartOptions)

    # Layout
    size: WidgetSize = WidgetSize.MEDIUM
    row: int = 0
    col: int = 0

    # Static data (for non-query widgets)
    static_data: Optional[Any] = None

    def add_query(self, query: DataQuery) -> "Widget":
        """Add a data query."""
        self.queries.append(query)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.chart_type.value,
            "queries": [q.to_dict() for q in self.queries],
            "size": self.size.value,
            "position": {"row": self.row, "col": self.col},
        }


@dataclass
class Panel:
    """A panel containing widgets."""
    id: str
    title: str

    # Widgets
    widgets: List[Widget] = field(default_factory=list)

    # Layout
    collapsed: bool = False

    def add_widget(self, widget: Widget) -> "Panel":
        """Add a widget to the panel."""
        self.widgets.append(widget)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "widgets": [w.to_dict() for w in self.widgets],
            "collapsed": self.collapsed,
        }


@dataclass
class TimeRange:
    """Time range for dashboard."""
    start: datetime
    end: datetime

    @classmethod
    def last(cls, duration: timedelta) -> "TimeRange":
        """Create time range for last N duration."""
        end = datetime.now()
        start = end - duration
        return cls(start=start, end=end)

    @classmethod
    def last_hour(cls) -> "TimeRange":
        return cls.last(timedelta(hours=1))

    @classmethod
    def last_day(cls) -> "TimeRange":
        return cls.last(timedelta(days=1))

    @classmethod
    def last_week(cls) -> "TimeRange":
        return cls.last(timedelta(weeks=1))


@dataclass
class Dashboard:
    """A complete dashboard."""
    id: str
    title: str
    description: str = ""

    # Content
    panels: List[Panel] = field(default_factory=list)

    # Variables
    variables: Dict[str, List[str]] = field(default_factory=dict)

    # Time
    time_range: TimeRange = field(default_factory=TimeRange.last_hour)
    refresh_interval: int = 30  # seconds

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""

    # Tags
    tags: List[str] = field(default_factory=list)

    def add_panel(self, panel: Panel) -> "Dashboard":
        """Add a panel to the dashboard."""
        self.panels.append(panel)
        self.updated_at = datetime.now()
        return self

    def add_variable(self, name: str, values: List[str]) -> "Dashboard":
        """Add a variable."""
        self.variables[name] = values
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "panels": [p.to_dict() for p in self.panels],
            "variables": self.variables,
            "refresh_interval": self.refresh_interval,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }

    def to_json(self) -> str:
        """Export as JSON."""
        return json.dumps(self.to_dict(), indent=2)


class DashboardBuilder:
    """
    Builder for creating dashboards.
    """

    def __init__(self, dashboard_id: str, title: str):
        self._dashboard = Dashboard(id=dashboard_id, title=title)
        self._current_panel: Optional[Panel] = None
        self._widget_counter = 0
        self._panel_counter = 0

    def description(self, desc: str) -> "DashboardBuilder":
        """Set description."""
        self._dashboard.description = desc
        return self

    def tags(self, *tags: str) -> "DashboardBuilder":
        """Set tags."""
        self._dashboard.tags = list(tags)
        return self

    def refresh(self, seconds: int) -> "DashboardBuilder":
        """Set refresh interval."""
        self._dashboard.refresh_interval = seconds
        return self

    def variable(self, name: str, values: List[str]) -> "DashboardBuilder":
        """Add a variable."""
        self._dashboard.add_variable(name, values)
        return self

    def panel(self, title: str) -> "DashboardBuilder":
        """Start a new panel."""
        self._panel_counter += 1
        panel_id = f"panel_{self._panel_counter}"

        self._current_panel = Panel(id=panel_id, title=title)
        self._dashboard.add_panel(self._current_panel)
        return self

    def widget(
        self,
        title: str,
        chart_type: ChartType = ChartType.LINE,
        metric: Optional[str] = None,
        size: WidgetSize = WidgetSize.MEDIUM,
    ) -> "DashboardBuilder":
        """Add a widget to current panel."""
        if not self._current_panel:
            self.panel("Default")

        self._widget_counter += 1
        widget_id = f"widget_{self._widget_counter}"

        widget = Widget(
            id=widget_id,
            title=title,
            chart_type=chart_type,
            size=size,
        )

        if metric:
            widget.add_query(DataQuery(metric_name=metric))

        self._current_panel.add_widget(widget)
        return self

    def stat(self, title: str, metric: str, unit: str = "") -> "DashboardBuilder":
        """Add a stat widget."""
        return self.widget(title, ChartType.STAT, metric, WidgetSize.SMALL)

    def line(self, title: str, metric: str, size: WidgetSize = WidgetSize.MEDIUM) -> "DashboardBuilder":
        """Add a line chart."""
        return self.widget(title, ChartType.LINE, metric, size)

    def gauge(self, title: str, metric: str) -> "DashboardBuilder":
        """Add a gauge."""
        return self.widget(title, ChartType.GAUGE, metric, WidgetSize.SMALL)

    def table(self, title: str, metric: str) -> "DashboardBuilder":
        """Add a table."""
        return self.widget(title, ChartType.TABLE, metric, WidgetSize.LARGE)

    def build(self) -> Dashboard:
        """Build the dashboard."""
        return self._dashboard


class DashboardEngine:
    """
    Dashboard engine for BAEL.

    Manages dashboards.
    """

    def __init__(self):
        # Dashboards
        self._dashboards: Dict[str, Dashboard] = {}

        # Metrics source (for data fetching)
        self._metrics_source: Optional[Any] = None

        # Stats
        self.stats = {
            "dashboards_created": 0,
            "widgets_rendered": 0,
        }

    def set_metrics_source(self, source: Any) -> None:
        """Set the metrics source for data fetching."""
        self._metrics_source = source

    def create(self, dashboard_id: str, title: str) -> DashboardBuilder:
        """Create a new dashboard."""
        return DashboardBuilder(dashboard_id, title)

    def save(self, dashboard: Dashboard) -> None:
        """Save a dashboard."""
        self._dashboards[dashboard.id] = dashboard
        self.stats["dashboards_created"] += 1

    def get(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def delete(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards."""
        return [
            {
                "id": d.id,
                "title": d.title,
                "panels_count": len(d.panels),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in self._dashboards.values()
        ]

    def render_widget(
        self,
        widget: Widget,
        time_range: Optional[TimeRange] = None,
    ) -> Dict[str, Any]:
        """
        Render a widget with data.

        Args:
            widget: The widget to render
            time_range: Optional time range

        Returns:
            Rendered widget data
        """
        time_range = time_range or TimeRange.last_hour()

        # Fetch data for each query
        series_data = []
        for query in widget.queries:
            data = self._fetch_data(query, time_range)
            series_data.append({
                "metric": query.metric_name,
                "data": data,
            })

        self.stats["widgets_rendered"] += 1

        return {
            "widget": widget.to_dict(),
            "series": series_data,
            "time_range": {
                "start": time_range.start.isoformat(),
                "end": time_range.end.isoformat(),
            },
        }

    def _fetch_data(
        self,
        query: DataQuery,
        time_range: TimeRange,
    ) -> List[Tuple[datetime, float]]:
        """Fetch data for a query."""
        # In real implementation, query from metrics source
        # For demo, generate sample data
        import random

        data = []
        current = time_range.start
        while current <= time_range.end:
            value = random.uniform(20, 80) + random.gauss(0, 5)
            data.append((current, value))
            current += timedelta(seconds=query.step_seconds)

        return data

    def export_dashboard(self, dashboard_id: str, format: str = "json") -> str:
        """Export dashboard."""
        dashboard = self.get(dashboard_id)
        if not dashboard:
            raise ValueError(f"Dashboard not found: {dashboard_id}")

        if format == "json":
            return dashboard.to_json()

        raise ValueError(f"Unsupported format: {format}")

    def import_dashboard(self, data: str, format: str = "json") -> Dashboard:
        """Import dashboard from data."""
        if format == "json":
            d = json.loads(data)
            dashboard = Dashboard(
                id=d["id"],
                title=d["title"],
                description=d.get("description", ""),
            )
            # Would need to reconstruct panels/widgets
            self.save(dashboard)
            return dashboard

        raise ValueError(f"Unsupported format: {format}")

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "dashboards_count": len(self._dashboards),
        }


def demo():
    """Demonstrate dashboard engine."""
    print("=" * 60)
    print("BAEL Dashboard Engine Demo")
    print("=" * 60)

    engine = DashboardEngine()

    # Create dashboard using builder
    print("\nCreating dashboard...")

    dashboard = (
        engine.create("system-overview", "System Overview")
        .description("Real-time system monitoring dashboard")
        .tags("system", "monitoring", "ops")
        .refresh(30)
        .variable("host", ["server-1", "server-2", "server-3"])

        # Overview panel
        .panel("System Health")
        .stat("CPU Usage", "cpu_percent", unit="%")
        .stat("Memory", "memory_used_gb", unit="GB")
        .stat("Disk", "disk_used_percent", unit="%")
        .gauge("Load", "load_avg")

        # Performance panel
        .panel("Performance Metrics")
        .line("Request Rate", "requests_per_second", WidgetSize.LARGE)
        .line("Response Time", "response_time_ms", WidgetSize.LARGE)

        # Errors panel
        .panel("Errors & Alerts")
        .line("Error Rate", "error_rate")
        .table("Recent Errors", "error_log")

        .build()
    )

    engine.save(dashboard)

    print(f"\nDashboard created: {dashboard.title}")
    print(f"  ID: {dashboard.id}")
    print(f"  Panels: {len(dashboard.panels)}")
    print(f"  Tags: {dashboard.tags}")

    for panel in dashboard.panels:
        print(f"\n  Panel: {panel.title}")
        for widget in panel.widgets:
            print(f"    - {widget.title} ({widget.chart_type.value})")

    # Render a widget
    print("\nRendering widget...")
    if dashboard.panels and dashboard.panels[0].widgets:
        widget = dashboard.panels[0].widgets[0]
        rendered = engine.render_widget(widget)
        print(f"  Widget: {rendered['widget']['title']}")
        print(f"  Data points: {len(rendered['series'][0]['data']) if rendered['series'] else 0}")

    # Export
    print("\nExporting dashboard (excerpt)...")
    exported = engine.export_dashboard(dashboard.id)
    print(exported[:300] + "...")

    # List dashboards
    print(f"\nDashboards: {engine.list_dashboards()}")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
