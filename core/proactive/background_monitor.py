"""
BAEL - Background Monitor
Continuous monitoring for proactive opportunities.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Proactive.Monitor")


class MonitorType(Enum):
    """Types of background monitors."""
    FILE_SYSTEM = "file_system"
    CLIPBOARD = "clipboard"
    SCREEN = "screen"
    PROCESS = "process"
    NETWORK = "network"
    TIME = "time"
    CUSTOM = "custom"


@dataclass
class MonitorEvent:
    """An event from a background monitor."""
    monitor_type: MonitorType
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class MonitorConfig:
    """Configuration for a monitor."""
    monitor_type: MonitorType
    enabled: bool = True
    interval_seconds: float = 60.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None


class BackgroundMonitor:
    """
    Background monitoring system for proactive opportunities.

    Features:
    - File system watching
    - Clipboard monitoring
    - Time-based triggers
    - Custom monitors
    - Event aggregation
    """

    def __init__(self):
        self._monitors: Dict[str, MonitorConfig] = {}
        self._events: List[MonitorEvent] = []
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._callbacks: List[Callable[[MonitorEvent], Awaitable[None]]] = []

        # Register default monitors
        self._setup_default_monitors()

    def _setup_default_monitors(self):
        """Setup default monitoring configurations."""
        # Time-based monitor (hourly check-ins)
        self.register_monitor(MonitorConfig(
            monitor_type=MonitorType.TIME,
            interval_seconds=3600,
            conditions={"type": "hourly_checkin"}
        ))

        # File system monitor for workspace
        self.register_monitor(MonitorConfig(
            monitor_type=MonitorType.FILE_SYSTEM,
            interval_seconds=30,
            conditions={"watch_dirs": ["."], "events": ["modified", "created"]}
        ))

    def register_monitor(self, config: MonitorConfig) -> str:
        """Register a new monitor."""
        monitor_id = f"{config.monitor_type.value}_{len(self._monitors)}"
        self._monitors[monitor_id] = config
        logger.debug(f"Registered monitor: {monitor_id}")
        return monitor_id

    def unregister_monitor(self, monitor_id: str) -> bool:
        """Unregister a monitor."""
        if monitor_id in self._monitors:
            del self._monitors[monitor_id]
            return True
        return False

    def add_event_callback(
        self,
        callback: Callable[[MonitorEvent], Awaitable[None]]
    ) -> None:
        """Add a callback for monitor events."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start all monitors."""
        if self._running:
            return

        self._running = True

        for monitor_id, config in self._monitors.items():
            if config.enabled:
                task = asyncio.create_task(
                    self._run_monitor(monitor_id, config)
                )
                self._tasks.append(task)

        logger.info(f"Started {len(self._tasks)} background monitors")

    async def stop(self) -> None:
        """Stop all monitors."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Background monitors stopped")

    async def _run_monitor(
        self,
        monitor_id: str,
        config: MonitorConfig
    ) -> None:
        """Run a single monitor loop."""
        logger.debug(f"Starting monitor: {monitor_id}")

        while self._running:
            try:
                events = await self._check_monitor(config)

                for event in events:
                    self._events.append(event)
                    await self._dispatch_event(event)

                await asyncio.sleep(config.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor {monitor_id} error: {e}")
                await asyncio.sleep(config.interval_seconds)

    async def _check_monitor(
        self,
        config: MonitorConfig
    ) -> List[MonitorEvent]:
        """Check a monitor for events."""
        events = []

        if config.monitor_type == MonitorType.TIME:
            events.extend(await self._check_time_monitor(config))

        elif config.monitor_type == MonitorType.FILE_SYSTEM:
            events.extend(await self._check_file_system_monitor(config))

        elif config.monitor_type == MonitorType.CLIPBOARD:
            events.extend(await self._check_clipboard_monitor(config))

        elif config.monitor_type == MonitorType.PROCESS:
            events.extend(await self._check_process_monitor(config))

        elif config.monitor_type == MonitorType.CUSTOM:
            if config.callback:
                try:
                    result = await config.callback()
                    if result:
                        events.append(MonitorEvent(
                            monitor_type=MonitorType.CUSTOM,
                            event_type="custom_trigger",
                            data=result
                        ))
                except Exception as e:
                    logger.warning(f"Custom monitor error: {e}")

        return events

    async def _check_time_monitor(
        self,
        config: MonitorConfig
    ) -> List[MonitorEvent]:
        """Check time-based conditions."""
        events = []
        conditions = config.conditions

        now = datetime.now()

        if conditions.get("type") == "hourly_checkin":
            # Generate hourly check-in event
            events.append(MonitorEvent(
                monitor_type=MonitorType.TIME,
                event_type="hourly_checkin",
                data={
                    "hour": now.hour,
                    "minute": now.minute,
                    "timestamp": time.time()
                }
            ))

        # Check for specific time triggers
        if "times" in conditions:
            for trigger_time in conditions["times"]:
                if now.strftime("%H:%M") == trigger_time:
                    events.append(MonitorEvent(
                        monitor_type=MonitorType.TIME,
                        event_type="scheduled_trigger",
                        data={"trigger_time": trigger_time}
                    ))

        return events

    async def _check_file_system_monitor(
        self,
        config: MonitorConfig
    ) -> List[MonitorEvent]:
        """Check file system for changes."""
        events = []
        conditions = config.conditions

        watch_dirs = conditions.get("watch_dirs", ["."])
        watched_events = conditions.get("events", ["modified"])

        for watch_dir in watch_dirs:
            if not os.path.exists(watch_dir):
                continue

            try:
                # Get current file states
                current_state = {}
                for root, dirs, files in os.walk(watch_dir):
                    # Limit depth
                    if root.count(os.sep) - watch_dir.count(os.sep) > 2:
                        continue

                    for file in files[:100]:  # Limit files
                        filepath = os.path.join(root, file)
                        try:
                            stat = os.stat(filepath)
                            current_state[filepath] = {
                                "mtime": stat.st_mtime,
                                "size": stat.st_size
                            }
                        except:
                            pass

                # Compare with cached state
                cache_key = f"fs_state_{watch_dir}"
                previous_state = getattr(self, cache_key, {})

                for filepath, info in current_state.items():
                    if filepath not in previous_state:
                        if "created" in watched_events:
                            events.append(MonitorEvent(
                                monitor_type=MonitorType.FILE_SYSTEM,
                                event_type="file_created",
                                data={"path": filepath}
                            ))
                    elif info["mtime"] != previous_state[filepath]["mtime"]:
                        if "modified" in watched_events:
                            events.append(MonitorEvent(
                                monitor_type=MonitorType.FILE_SYSTEM,
                                event_type="file_modified",
                                data={"path": filepath}
                            ))

                # Check for deleted files
                for filepath in previous_state:
                    if filepath not in current_state:
                        if "deleted" in watched_events:
                            events.append(MonitorEvent(
                                monitor_type=MonitorType.FILE_SYSTEM,
                                event_type="file_deleted",
                                data={"path": filepath}
                            ))

                # Update cache
                setattr(self, cache_key, current_state)

            except Exception as e:
                logger.warning(f"File system monitor error: {e}")

        return events[:10]  # Limit events per check

    async def _check_clipboard_monitor(
        self,
        config: MonitorConfig
    ) -> List[MonitorEvent]:
        """Check clipboard for changes."""
        events = []

        try:
            import pyperclip

            current = pyperclip.paste()
            previous = getattr(self, "_last_clipboard", "")

            if current != previous and current:
                events.append(MonitorEvent(
                    monitor_type=MonitorType.CLIPBOARD,
                    event_type="clipboard_changed",
                    data={
                        "content": current[:500],
                        "length": len(current)
                    }
                ))
                self._last_clipboard = current

        except ImportError:
            pass  # pyperclip not available
        except Exception as e:
            logger.debug(f"Clipboard monitor error: {e}")

        return events

    async def _check_process_monitor(
        self,
        config: MonitorConfig
    ) -> List[MonitorEvent]:
        """Check running processes."""
        events = []

        try:
            import subprocess

            # Get list of running processes (macOS/Linux)
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Look for specific processes if configured
            watch_processes = config.conditions.get("processes", [])

            for process in watch_processes:
                if process.lower() in result.stdout.lower():
                    events.append(MonitorEvent(
                        monitor_type=MonitorType.PROCESS,
                        event_type="process_running",
                        data={"process": process}
                    ))

        except Exception as e:
            logger.debug(f"Process monitor error: {e}")

        return events

    async def _dispatch_event(self, event: MonitorEvent) -> None:
        """Dispatch event to callbacks."""
        for callback in self._callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    def get_recent_events(
        self,
        monitor_type: Optional[MonitorType] = None,
        limit: int = 50
    ) -> List[MonitorEvent]:
        """Get recent monitoring events."""
        events = self._events

        if monitor_type:
            events = [e for e in events if e.monitor_type == monitor_type]

        # Sort by timestamp, most recent first
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    def clear_events(self) -> None:
        """Clear event history."""
        self._events.clear()

    def get_monitor_status(self) -> Dict[str, Any]:
        """Get status of all monitors."""
        return {
            "running": self._running,
            "monitor_count": len(self._monitors),
            "active_tasks": len(self._tasks),
            "event_count": len(self._events),
            "monitors": {
                mid: {
                    "type": config.monitor_type.value,
                    "enabled": config.enabled,
                    "interval": config.interval_seconds
                }
                for mid, config in self._monitors.items()
            }
        }


# Global instance
_background_monitor: Optional[BackgroundMonitor] = None


def get_background_monitor() -> BackgroundMonitor:
    """Get or create background monitor instance."""
    global _background_monitor
    if _background_monitor is None:
        _background_monitor = BackgroundMonitor()
    return _background_monitor
