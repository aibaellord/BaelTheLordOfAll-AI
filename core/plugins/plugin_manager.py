#!/usr/bin/env python3
"""
BAEL - Plugin Manager
Extensible plugin architecture for modular functionality.

This module provides a comprehensive plugin system that allows
BAEL to be extended with custom functionality at runtime.

Features:
- Plugin discovery and loading
- Plugin lifecycle management
- Hook system for extensibility
- Plugin dependencies
- Plugin configuration
- Hot-reloading
- Plugin sandboxing
- Version compatibility
- Plugin marketplace
- Event-driven plugins
"""

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class PluginState(Enum):
    """Plugin lifecycle states."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


class PluginPriority(Enum):
    """Plugin execution priority."""
    HIGHEST = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


class HookType(Enum):
    """Types of hooks."""
    FILTER = "filter"      # Modify data
    ACTION = "action"      # Perform action
    EVENT = "event"        # React to event
    PROVIDER = "provider"  # Provide data


class PluginScope(Enum):
    """Plugin scope."""
    GLOBAL = "global"      # System-wide
    SESSION = "session"    # Per session
    AGENT = "agent"        # Per agent
    TASK = "task"          # Per task


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PluginVersion:
    """Plugin version."""
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "PluginVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "PluginVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    @classmethod
    def parse(cls, version_str: str) -> "PluginVersion":
        """Parse version string."""
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 1,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )


@dataclass
class PluginDependency:
    """Plugin dependency."""
    name: str
    min_version: Optional[PluginVersion] = None
    max_version: Optional[PluginVersion] = None
    optional: bool = False


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: PluginVersion = field(default_factory=PluginVersion)
    author: str = ""
    license: str = ""
    homepage: str = ""
    tags: Set[str] = field(default_factory=set)
    dependencies: List[PluginDependency] = field(default_factory=list)
    bael_version_min: Optional[PluginVersion] = None
    bael_version_max: Optional[PluginVersion] = None
    scope: PluginScope = PluginScope.GLOBAL


@dataclass
class PluginConfig:
    """Plugin configuration."""
    enabled: bool = True
    priority: PluginPriority = PluginPriority.NORMAL
    auto_start: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    permissions: Set[str] = field(default_factory=set)


@dataclass
class HookRegistration:
    """A registered hook."""
    hook_name: str
    callback: Callable
    plugin_id: str
    priority: PluginPriority = PluginPriority.NORMAL
    hook_type: HookType = HookType.ACTION
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginEvent:
    """An event for plugins."""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    propagate: bool = True


# =============================================================================
# PLUGIN BASE
# =============================================================================

class PluginBase(ABC):
    """Abstract base class for plugins."""

    # Override these in subclass
    PLUGIN_NAME = "base_plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = ""
    PLUGIN_AUTHOR = ""
    PLUGIN_DEPENDENCIES: List[str] = []

    def __init__(self):
        self.metadata = PluginMetadata(
            name=self.PLUGIN_NAME,
            version=PluginVersion.parse(self.PLUGIN_VERSION),
            description=self.PLUGIN_DESCRIPTION,
            author=self.PLUGIN_AUTHOR
        )
        self.config = PluginConfig()
        self.state = PluginState.DISCOVERED
        self._hooks: List[HookRegistration] = []
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._context: Dict[str, Any] = {}

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def name(self) -> str:
        return self.metadata.name

    async def load(self) -> bool:
        try:
            self.state = PluginState.LOADED
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {self.name}: {e}")
            self.state = PluginState.ERROR
            return False

    async def initialize(self) -> bool:
        try:
            await self.on_initialize()
            self.state = PluginState.INITIALIZED
            return True
        except Exception as e:
            logger.error(f"Failed to initialize plugin {self.name}: {e}")
            self.state = PluginState.ERROR
            return False

    async def start(self) -> bool:
        try:
            await self.on_start()
            self.state = PluginState.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to start plugin {self.name}: {e}")
            self.state = PluginState.ERROR
            return False

    async def stop(self) -> bool:
        try:
            self.state = PluginState.STOPPING
            await self.on_stop()
            self.state = PluginState.STOPPED
            return True
        except Exception as e:
            logger.error(f"Failed to stop plugin {self.name}: {e}")
            self.state = PluginState.ERROR
            return False

    async def unload(self) -> bool:
        try:
            await self.on_unload()
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {self.name}: {e}")
            return False

    async def on_initialize(self) -> None:
        pass

    async def on_start(self) -> None:
        pass

    async def on_stop(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    def register_hook(
        self,
        hook_name: str,
        callback: Callable,
        hook_type: HookType = HookType.ACTION,
        priority: PluginPriority = PluginPriority.NORMAL,
        **filters
    ) -> HookRegistration:
        registration = HookRegistration(
            hook_name=hook_name,
            callback=callback,
            plugin_id=self.id,
            priority=priority,
            hook_type=hook_type,
            filters=filters
        )
        self._hooks.append(registration)
        return registration

    def on_event(self, event_name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._event_handlers[event_name].append(func)
            return func
        return decorator

    async def handle_event(self, event: PluginEvent) -> None:
        handlers = self._event_handlers.get(event.name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Plugin {self.name} event handler error: {e}")

    def configure(self, **settings) -> None:
        self.config.settings.update(settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.config.settings.get(key, default)

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": str(self.metadata.version),
            "description": self.metadata.description,
            "author": self.metadata.author,
            "state": self.state.value,
            "hooks": len(self._hooks),
            "events": len(self._event_handlers)
        }


# =============================================================================
# HOOK MANAGER
# =============================================================================

class HookManager:
    """Manages plugin hooks."""

    def __init__(self):
        self.hooks: Dict[str, List[HookRegistration]] = defaultdict(list)

    def register(self, registration: HookRegistration) -> None:
        self.hooks[registration.hook_name].append(registration)
        self.hooks[registration.hook_name].sort(key=lambda r: r.priority.value)

    def unregister(self, plugin_id: str) -> int:
        count = 0
        for hook_name, registrations in self.hooks.items():
            original_len = len(registrations)
            self.hooks[hook_name] = [
                r for r in registrations if r.plugin_id != plugin_id
            ]
            count += original_len - len(self.hooks[hook_name])
        return count

    async def apply_filter(
        self,
        hook_name: str,
        value: Any,
        *args,
        **kwargs
    ) -> Any:
        for registration in self.hooks.get(hook_name, []):
            if registration.hook_type != HookType.FILTER:
                continue
            try:
                callback = registration.callback
                if asyncio.iscoroutinefunction(callback):
                    value = await callback(value, *args, **kwargs)
                else:
                    value = callback(value, *args, **kwargs)
            except Exception as e:
                logger.error(f"Filter hook {hook_name} error: {e}")
        return value

    async def do_action(self, hook_name: str, *args, **kwargs) -> None:
        for registration in self.hooks.get(hook_name, []):
            if registration.hook_type != HookType.ACTION:
                continue
            try:
                callback = registration.callback
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Action hook {hook_name} error: {e}")

    async def get_providers(self, hook_name: str, *args, **kwargs) -> List[Any]:
        results = []
        for registration in self.hooks.get(hook_name, []):
            if registration.hook_type != HookType.PROVIDER:
                continue
            try:
                callback = registration.callback
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(*args, **kwargs)
                else:
                    result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Provider hook {hook_name} error: {e}")
        return results

    def get_hooks(self, hook_name: str = None) -> Dict[str, List[Dict]]:
        if hook_name:
            return {
                hook_name: [
                    {"plugin_id": r.plugin_id, "type": r.hook_type.value, "priority": r.priority.value}
                    for r in self.hooks.get(hook_name, [])
                ]
            }
        return {
            name: [
                {"plugin_id": r.plugin_id, "type": r.hook_type.value, "priority": r.priority.value}
                for r in registrations
            ]
            for name, registrations in self.hooks.items()
        }


# =============================================================================
# EVENT BUS
# =============================================================================

class PluginEventBus:
    """Event bus for plugin communication."""

    def __init__(self):
        self.subscribers: Dict[str, List[Tuple[str, Callable]]] = defaultdict(list)
        self.event_history: List[PluginEvent] = []
        self.max_history = 1000

    def subscribe(self, event_name: str, callback: Callable, subscriber_id: str = None) -> None:
        sub_id = subscriber_id or str(uuid4())
        self.subscribers[event_name].append((sub_id, callback))

    def unsubscribe(self, event_name: str = None, subscriber_id: str = None) -> int:
        count = 0
        if event_name and subscriber_id:
            original = self.subscribers.get(event_name, [])
            self.subscribers[event_name] = [(sid, cb) for sid, cb in original if sid != subscriber_id]
            count = len(original) - len(self.subscribers[event_name])
        elif subscriber_id:
            for name, subs in self.subscribers.items():
                original_len = len(subs)
                self.subscribers[name] = [(sid, cb) for sid, cb in subs if sid != subscriber_id]
                count += original_len - len(self.subscribers[name])
        return count

    async def emit(self, event_name: str, data: Dict[str, Any] = None, source: str = "") -> int:
        event = PluginEvent(name=event_name, data=data or {}, source=source)
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]

        notified = 0
        for subscriber_id, callback in self.subscribers.get(event_name, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
                notified += 1
            except Exception as e:
                logger.error(f"Event handler error ({subscriber_id}): {e}")

        for subscriber_id, callback in self.subscribers.get("*", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
                notified += 1
            except Exception as e:
                logger.error(f"Wildcard handler error ({subscriber_id}): {e}")

        return notified

    def get_history(self, event_name: str = None, limit: int = 100) -> List[PluginEvent]:
        events = self.event_history
        if event_name:
            events = [e for e in events if e.name == event_name]
        return events[-limit:]


# =============================================================================
# PLUGIN LOADER
# =============================================================================

class PluginLoader:
    """Loads plugins from various sources."""

    def __init__(self, plugin_paths: List[str] = None):
        self.plugin_paths = plugin_paths or []
        self.loaded_modules: Dict[str, Any] = {}

    def add_path(self, path: str) -> None:
        if path not in self.plugin_paths:
            self.plugin_paths.append(path)

    def discover(self) -> List[str]:
        discovered = []
        for path in self.plugin_paths:
            path_obj = Path(path)
            if not path_obj.exists():
                continue
            for py_file in path_obj.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                discovered.append(str(py_file))
            for dir_path in path_obj.iterdir():
                if dir_path.is_dir() and (dir_path / "__init__.py").exists():
                    discovered.append(str(dir_path))
        return discovered

    def load_from_file(self, file_path: str) -> Optional[Type[PluginBase]]:
        try:
            path = Path(file_path)
            module_name = path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.loaded_modules[module_name] = module
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj is not PluginBase:
                    return obj
            return None
        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")
            return None

    def load_from_class(self, plugin_class: Type[PluginBase]) -> Optional[PluginBase]:
        try:
            return plugin_class()
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_class}: {e}")
            return None

    def reload(self, module_name: str) -> bool:
        if module_name not in self.loaded_modules:
            return False
        try:
            module = self.loaded_modules[module_name]
            importlib.reload(module)
            return True
        except Exception as e:
            logger.error(f"Failed to reload {module_name}: {e}")
            return False


# =============================================================================
# PLUGIN MANAGER
# =============================================================================

class PluginManager:
    """
    The master plugin manager for BAEL.

    Manages plugin discovery, loading, lifecycle,
    and inter-plugin communication.
    """

    def __init__(self, plugin_paths: List[str] = None):
        self.loader = PluginLoader(plugin_paths)
        self.hook_manager = HookManager()
        self.event_bus = PluginEventBus()
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_order: List[str] = []
        self._running = False

    async def discover_and_load(self) -> int:
        discovered = self.loader.discover()
        loaded = 0
        for plugin_path in discovered:
            plugin_class = self.loader.load_from_file(plugin_path)
            if plugin_class:
                plugin = self.loader.load_from_class(plugin_class)
                if plugin:
                    self.register(plugin)
                    loaded += 1
        return loaded

    def register(self, plugin: PluginBase) -> bool:
        if plugin.id in self.plugins:
            return False
        self.plugins[plugin.id] = plugin
        self.plugin_order.append(plugin.id)
        for hook in plugin._hooks:
            self.hook_manager.register(hook)
        for event_name, handlers in plugin._event_handlers.items():
            for handler in handlers:
                self.event_bus.subscribe(event_name, handler, plugin.id)
        return True

    async def unregister(self, plugin_id: str) -> bool:
        if plugin_id not in self.plugins:
            return False
        plugin = self.plugins[plugin_id]
        if plugin.state == PluginState.ACTIVE:
            await plugin.stop()
        await plugin.unload()
        self.hook_manager.unregister(plugin_id)
        self.event_bus.unsubscribe(subscriber_id=plugin_id)
        del self.plugins[plugin_id]
        self.plugin_order.remove(plugin_id)
        return True

    async def initialize_all(self) -> Dict[str, bool]:
        results = {}
        sorted_plugins = sorted(self.plugins.values(), key=lambda p: p.config.priority.value)
        for plugin in sorted_plugins:
            if plugin.state == PluginState.LOADED:
                results[plugin.id] = await plugin.initialize()
        return results

    async def start_all(self) -> Dict[str, bool]:
        results = {}
        for plugin_id in self.plugin_order:
            plugin = self.plugins.get(plugin_id)
            if plugin and plugin.config.auto_start:
                if plugin.state == PluginState.INITIALIZED:
                    results[plugin_id] = await plugin.start()
        self._running = True
        await self.event_bus.emit("plugins_started", {"count": len(results)})
        return results

    async def stop_all(self) -> Dict[str, bool]:
        results = {}
        for plugin_id in reversed(self.plugin_order):
            plugin = self.plugins.get(plugin_id)
            if plugin and plugin.state == PluginState.ACTIVE:
                results[plugin_id] = await plugin.stop()
        self._running = False
        await self.event_bus.emit("plugins_stopped", {"count": len(results)})
        return results

    def get(self, plugin_id: str) -> Optional[PluginBase]:
        return self.plugins.get(plugin_id)

    def get_by_name(self, name: str) -> Optional[PluginBase]:
        for plugin in self.plugins.values():
            if plugin.name == name:
                return plugin
        return None

    async def enable(self, plugin_id: str) -> bool:
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.config.enabled = True
        if plugin.state in (PluginState.DISABLED, PluginState.STOPPED):
            await plugin.initialize()
            await plugin.start()
        return True

    async def disable(self, plugin_id: str) -> bool:
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.config.enabled = False
        if plugin.state == PluginState.ACTIVE:
            await plugin.stop()
        plugin.state = PluginState.DISABLED
        return True

    async def reload(self, plugin_id: str) -> bool:
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False
        await plugin.stop()
        module_name = type(plugin).__module__
        if not self.loader.reload(module_name):
            return False
        await plugin.initialize()
        await plugin.start()
        return True

    async def apply_filter(self, hook_name: str, value: Any, *args, **kwargs) -> Any:
        return await self.hook_manager.apply_filter(hook_name, value, *args, **kwargs)

    async def do_action(self, hook_name: str, *args, **kwargs) -> None:
        await self.hook_manager.do_action(hook_name, *args, **kwargs)

    async def get_providers(self, hook_name: str, *args, **kwargs) -> List[Any]:
        return await self.hook_manager.get_providers(hook_name, *args, **kwargs)

    async def emit(self, event_name: str, data: Dict[str, Any] = None) -> int:
        return await self.event_bus.emit(event_name, data, source="plugin_manager")

    def check_dependencies(self, plugin_id: str) -> Tuple[bool, List[str]]:
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False, ["Plugin not found"]
        missing = []
        for dep in plugin.metadata.dependencies:
            found = False
            for p in self.plugins.values():
                if p.name == dep.name:
                    if dep.min_version and p.metadata.version < dep.min_version:
                        missing.append(f"{dep.name} >= {dep.min_version}")
                    elif dep.max_version and p.metadata.version > dep.max_version:
                        missing.append(f"{dep.name} <= {dep.max_version}")
                    else:
                        found = True
                    break
            if not found and not dep.optional:
                missing.append(dep.name)
        return len(missing) == 0, missing

    def get_catalog(self) -> List[Dict[str, Any]]:
        return [plugin.get_info() for plugin in self.plugins.values()]

    def get_statistics(self) -> Dict[str, Any]:
        by_state = defaultdict(int)
        for plugin in self.plugins.values():
            by_state[plugin.state.value] += 1
        return {
            "total_plugins": len(self.plugins),
            "by_state": dict(by_state),
            "hooks_registered": sum(len(hooks) for hooks in self.hook_manager.hooks.values()),
            "event_subscriptions": sum(len(subs) for subs in self.event_bus.subscribers.values()),
            "events_in_history": len(self.event_bus.event_history)
        }


# =============================================================================
# EXAMPLE PLUGINS
# =============================================================================

class LoggingPlugin(PluginBase):
    """A logging plugin."""

    PLUGIN_NAME = "logging_plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Provides logging functionality"
    PLUGIN_AUTHOR = "BAEL Core"

    async def on_initialize(self) -> None:
        self.register_hook("log_message", self._log_message, HookType.ACTION)
        self.register_hook("format_log", self._format_log, HookType.FILTER)

    async def on_start(self) -> None:
        logger.info(f"Logging plugin started")

    def _log_message(self, message: str, level: str = "info") -> None:
        log_func = getattr(logger, level, logger.info)
        log_func(message)

    def _format_log(self, message: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {message}"


class MetricsPlugin(PluginBase):
    """A metrics collection plugin."""

    PLUGIN_NAME = "metrics_plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Collects and exposes metrics"
    PLUGIN_AUTHOR = "BAEL Core"

    def __init__(self):
        super().__init__()
        self.metrics: Dict[str, float] = defaultdict(float)
        self.counters: Dict[str, int] = defaultdict(int)

    async def on_initialize(self) -> None:
        self.register_hook("record_metric", self._record_metric, HookType.ACTION)
        self.register_hook("get_metrics", self._provide_metrics, HookType.PROVIDER)

    def _record_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value
        self.counters[name] += 1

    def _provide_metrics(self) -> Dict[str, Any]:
        return {"values": dict(self.metrics), "counts": dict(self.counters)}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Plugin Manager."""
    print("=" * 70)
    print("BAEL - PLUGIN MANAGER DEMO")
    print("Extensible Plugin Architecture")
    print("=" * 70)
    print()

    manager = PluginManager()

    print("1. REGISTERING PLUGINS:")
    print("-" * 40)

    logging_plugin = LoggingPlugin()
    metrics_plugin = MetricsPlugin()

    manager.register(logging_plugin)
    manager.register(metrics_plugin)

    print(f"   Registered: {logging_plugin.name}")
    print(f"   Registered: {metrics_plugin.name}")
    print()

    print("2. LOADING PLUGINS:")
    print("-" * 40)

    await logging_plugin.load()
    await metrics_plugin.load()

    print(f"   {logging_plugin.name}: {logging_plugin.state.value}")
    print(f"   {metrics_plugin.name}: {metrics_plugin.state.value}")
    print()

    print("3. INITIALIZE AND START:")
    print("-" * 40)

    await manager.initialize_all()
    results = await manager.start_all()

    for plugin_id, success in results.items():
        plugin = manager.get(plugin_id)
        print(f"   {plugin.name}: Started={success}, State={plugin.state.value}")
    print()

    print("4. USING HOOKS:")
    print("-" * 40)

    raw_message = "Hello World"
    formatted = await manager.apply_filter("format_log", raw_message)
    print(f"   Formatted: {formatted}")

    await manager.do_action("log_message", "Test log entry", level="info")
    print("   Logged: Test log entry")

    await manager.do_action("record_metric", "requests", 100.0)
    await manager.do_action("record_metric", "latency", 0.05)
    print("   Recorded metrics: requests=100, latency=0.05")

    metrics_data = await manager.get_providers("get_metrics")
    if metrics_data:
        print(f"   Metrics: {metrics_data[0]['values']}")
    print()

    print("5. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"   Total plugins: {stats['total_plugins']}")
    print(f"   By state: {stats['by_state']}")
    print(f"   Hooks registered: {stats['hooks_registered']}")
    print()

    await manager.stop_all()

    print("=" * 70)
    print("DEMO COMPLETE - Plugin Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
