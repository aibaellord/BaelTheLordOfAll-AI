"""
BAEL UI Integration Service - Backend API for React Dashboard
Real-time WebSocket support, dashboard widgets, layout management, theme support.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Dashboard widget types."""
    SYSTEM_STATS = "system_stats"
    VISION_FEED = "vision_feed"
    VIDEO_STREAM = "video_stream"
    AUDIO_PLAYER = "audio_player"
    LOGS = "logs"
    METRICS = "metrics"
    WORKFLOW_STATUS = "workflow_status"
    MEMORY_GRAPH = "memory_graph"
    CONSENSUS_HEALTH = "consensus_health"
    REPLICATION_STATUS = "replication_status"
    PERFORMANCE_CHART = "performance_chart"
    ALERTS = "alerts"
    NETWORK_MAP = "network_map"
    RESOURCE_USAGE = "resource_usage"
    MODEL_PERFORMANCE = "model_performance"


class Theme(Enum):
    """UI themes."""
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


@dataclass
class Widget:
    """Dashboard widget definition."""
    widget_id: str
    type: WidgetType
    title: str
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: int = 5000  # milliseconds
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardLayout:
    """Dashboard layout definition."""
    layout_id: str
    name: str
    user_id: str
    widgets: List[Widget] = field(default_factory=list)
    theme: Theme = Theme.AUTO
    grid_cols: int = 12
    grid_rows: int = 8
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_default: bool = False


@dataclass
class SystemStats:
    """Current system statistics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_workflows: int
    running_nodes: int
    consensus_latency_ms: float
    replication_lag_ms: float
    vision_fps: float
    video_fps: float
    audio_streams: int
    network_latency_ms: float
    error_rate: float  # 0-1


@dataclass
class WidgetData:
    """Real-time widget data."""
    widget_id: str
    timestamp: datetime
    data: Dict[str, Any]
    status: str  # loading, ready, error


@dataclass
class DashboardUpdate:
    """WebSocket message for dashboard update."""
    type: str  # "stats", "log", "alert", "workflow_update"
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DashboardService:
    """Backend service managing dashboard state and updates."""

    def __init__(self):
        self.layouts: Dict[str, DashboardLayout] = {}
        self.user_layouts: Dict[str, List[str]] = {}  # user_id -> layout_ids
        self.widget_subscriptions: Dict[str, Set[str]] = {}  # layout_id -> subscriber_ids
        self.active_subscribers: Dict[str, Any] = {}  # subscriber_id -> connection
        self.system_stats_history: List[SystemStats] = []
        self.alerts: List[Dict[str, Any]] = []

        logger.info("DashboardService initialized")

    async def create_layout(
        self,
        user_id: str,
        name: str,
        widgets: Optional[List[Widget]] = None,
        is_default: bool = False
    ) -> DashboardLayout:
        """Create new dashboard layout."""

        layout_id = str(uuid.uuid4())
        layout = DashboardLayout(
            layout_id=layout_id,
            name=name,
            user_id=user_id,
            widgets=widgets or self._create_default_widgets(),
            is_default=is_default
        )

        self.layouts[layout_id] = layout

        if user_id not in self.user_layouts:
            self.user_layouts[user_id] = []

        self.user_layouts[user_id].append(layout_id)

        logger.info(f"Created layout {layout_id} for user {user_id}")

        return layout

    def _create_default_widgets(self) -> List[Widget]:
        """Create default widgets for new layout."""
        return [
            Widget(
                widget_id=str(uuid.uuid4()),
                type=WidgetType.SYSTEM_STATS,
                title="System Status",
                position={"x": 0, "y": 0, "width": 3, "height": 2}
            ),
            Widget(
                widget_id=str(uuid.uuid4()),
                type=WidgetType.METRICS,
                title="Performance Metrics",
                position={"x": 3, "y": 0, "width": 3, "height": 2}
            ),
            Widget(
                widget_id=str(uuid.uuid4()),
                type=WidgetType.LOGS,
                title="System Logs",
                position={"x": 6, "y": 0, "width": 6, "height": 4}
            ),
            Widget(
                widget_id=str(uuid.uuid4()),
                type=WidgetType.WORKFLOW_STATUS,
                title="Workflow Executions",
                position={"x": 0, "y": 2, "width": 6, "height": 2}
            ),
            Widget(
                widget_id=str(uuid.uuid4()),
                type=WidgetType.ALERTS,
                title="System Alerts",
                position={"x": 0, "y": 4, "width": 12, "height": 2}
            ),
        ]

    async def update_layout(
        self,
        layout_id: str,
        name: Optional[str] = None,
        widgets: Optional[List[Widget]] = None,
        theme: Optional[Theme] = None
    ) -> Optional[DashboardLayout]:
        """Update dashboard layout."""

        if layout_id not in self.layouts:
            return None

        layout = self.layouts[layout_id]

        if name:
            layout.name = name
        if widgets:
            layout.widgets = widgets
        if theme:
            layout.theme = theme

        layout.updated_at = datetime.utcnow()

        # Notify subscribers of update
        await self._broadcast_to_layout(
            layout_id,
            DashboardUpdate(
                type="layout_update",
                data=asdict(layout)
            )
        )

        return layout

    async def get_system_stats(self) -> SystemStats:
        """Get current system statistics."""
        # In production, collect from actual system
        stats = SystemStats(
            timestamp=datetime.utcnow(),
            cpu_usage=45.2,
            memory_usage=62.8,
            disk_usage=71.3,
            active_workflows=12,
            running_nodes=48,
            consensus_latency_ms=25.3,
            replication_lag_ms=5.2,
            vision_fps=450.0,
            video_fps=150.0,
            audio_streams=8,
            network_latency_ms=12.5,
            error_rate=0.001
        )

        self.system_stats_history.append(stats)

        # Keep last 1000 entries
        if len(self.system_stats_history) > 1000:
            self.system_stats_history = self.system_stats_history[-1000:]

        return stats

    async def get_widget_data(
        self,
        layout_id: str,
        widget_id: str
    ) -> Optional[WidgetData]:
        """Get data for specific widget."""

        if layout_id not in self.layouts:
            return None

        layout = self.layouts[layout_id]
        widget = next(
            (w for w in layout.widgets if w.widget_id == widget_id),
            None
        )

        if not widget:
            return None

        # Generate widget data based on type
        widget_data = await self._generate_widget_data(widget)

        return WidgetData(
            widget_id=widget_id,
            timestamp=datetime.utcnow(),
            data=widget_data,
            status="ready"
        )

    async def _generate_widget_data(self, widget: Widget) -> Dict[str, Any]:
        """Generate data for a widget based on its type."""

        if widget.type == WidgetType.SYSTEM_STATS:
            stats = await self.get_system_stats()
            return {
                "cpu": stats.cpu_usage,
                "memory": stats.memory_usage,
                "disk": stats.disk_usage,
                "timestamp": stats.timestamp.isoformat()
            }

        elif widget.type == WidgetType.METRICS:
            return {
                "consensus_latency_ms": 25.3,
                "replication_lag_ms": 5.2,
                "vision_fps": 450.0,
                "video_fps": 150.0,
                "error_rate": 0.001
            }

        elif widget.type == WidgetType.WORKFLOW_STATUS:
            return {
                "total": 150,
                "running": 12,
                "completed": 130,
                "failed": 8,
                "recent": [
                    {
                        "workflow_id": f"wf-{i}",
                        "status": ["completed", "running", "failed"][i % 3],
                        "progress": (i * 7) % 100
                    }
                    for i in range(5)
                ]
            }

        elif widget.type == WidgetType.LOGS:
            return {
                "logs": [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "info",
                        "message": f"System operation {i}"
                    }
                    for i in range(10)
                ]
            }

        elif widget.type == WidgetType.ALERTS:
            return {
                "critical": 0,
                "warning": 2,
                "info": 5,
                "alerts": self.alerts[-10:]
            }

        else:
            return {}

    async def add_alert(
        self,
        severity: str,
        title: str,
        message: str,
        source: str
    ) -> Dict[str, Any]:
        """Add system alert."""

        alert = {
            "alert_id": str(uuid.uuid4()),
            "severity": severity,
            "title": title,
            "message": message,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
            "acknowledged": False
        }

        self.alerts.append(alert)

        # Keep last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

        # Broadcast alert to all subscribers
        for layout_id in self.widget_subscriptions.keys():
            await self._broadcast_to_layout(
                layout_id,
                DashboardUpdate(
                    type="alert",
                    data=alert
                )
            )

        return alert

    async def subscribe_to_layout(
        self,
        layout_id: str,
        subscriber_id: str,
        connection: Any
    ):
        """Subscribe to layout updates."""

        if layout_id not in self.widget_subscriptions:
            self.widget_subscriptions[layout_id] = set()

        self.widget_subscriptions[layout_id].add(subscriber_id)
        self.active_subscribers[subscriber_id] = connection

        logger.info(f"Subscriber {subscriber_id} subscribed to layout {layout_id}")

    async def unsubscribe_from_layout(
        self,
        layout_id: str,
        subscriber_id: str
    ):
        """Unsubscribe from layout updates."""

        if layout_id in self.widget_subscriptions:
            self.widget_subscriptions[layout_id].discard(subscriber_id)

        self.active_subscribers.pop(subscriber_id, None)

        logger.info(f"Subscriber {subscriber_id} unsubscribed from layout {layout_id}")

    async def _broadcast_to_layout(
        self,
        layout_id: str,
        update: DashboardUpdate
    ):
        """Broadcast update to all subscribers of a layout."""

        subscribers = self.widget_subscriptions.get(layout_id, set())

        message = {
            "type": update.type,
            "data": update.data,
            "timestamp": update.timestamp.isoformat()
        }

        for subscriber_id in subscribers:
            connection = self.active_subscribers.get(subscriber_id)
            if connection:
                try:
                    # In production, send via WebSocket
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to subscriber {subscriber_id}: {e}")

    async def get_dashboard_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get dashboard metrics for specified time period."""

        # Filter stats for time period
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        recent_stats = [
            s for s in self.system_stats_history
            if s.timestamp.timestamp() >= cutoff_time
        ]

        if not recent_stats:
            return {}

        # Calculate statistics
        cpu_values = [s.cpu_usage for s in recent_stats]
        memory_values = [s.memory_usage for s in recent_stats]

        return {
            "period_hours": hours,
            "sample_count": len(recent_stats),
            "cpu": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "current": cpu_values[-1] if cpu_values else 0
            },
            "memory": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "current": memory_values[-1] if memory_values else 0
            },
            "alerts_count": len(self.alerts)
        }


class UIIntegrationAPI:
    """REST API for UI integration."""

    def __init__(self, dashboard_service: DashboardService):
        self.dashboard = dashboard_service
        logger.info("UIIntegrationAPI initialized")

    async def get_user_dashboards(self, user_id: str) -> List[DashboardLayout]:
        """Get all dashboards for user."""
        layout_ids = self.dashboard.user_layouts.get(user_id, [])
        return [self.dashboard.layouts[lid] for lid in layout_ids if lid in self.dashboard.layouts]

    async def get_dashboard(self, layout_id: str) -> Optional[DashboardLayout]:
        """Get specific dashboard."""
        return self.dashboard.layouts.get(layout_id)

    async def create_dashboard(
        self,
        user_id: str,
        name: str,
        is_default: bool = False
    ) -> DashboardLayout:
        """Create new dashboard."""
        return await self.dashboard.create_layout(user_id, name, is_default=is_default)

    async def update_dashboard(
        self,
        layout_id: str,
        updates: Dict[str, Any]
    ) -> Optional[DashboardLayout]:
        """Update dashboard."""
        return await self.dashboard.update_layout(layout_id, **updates)

    async def add_widget(
        self,
        layout_id: str,
        widget: Widget
    ) -> Optional[DashboardLayout]:
        """Add widget to dashboard."""

        layout = self.dashboard.layouts.get(layout_id)
        if not layout:
            return None

        layout.widgets.append(widget)
        layout.updated_at = datetime.utcnow()

        return layout

    async def remove_widget(
        self,
        layout_id: str,
        widget_id: str
    ) -> Optional[DashboardLayout]:
        """Remove widget from dashboard."""

        layout = self.dashboard.layouts.get(layout_id)
        if not layout:
            return None

        layout.widgets = [w for w in layout.widgets if w.widget_id != widget_id]
        layout.updated_at = datetime.utcnow()

        return layout

    async def get_system_stats(self) -> SystemStats:
        """Get current system statistics."""
        return await self.dashboard.get_system_stats()

    async def get_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get system metrics."""
        return await self.dashboard.get_dashboard_metrics(hours)
