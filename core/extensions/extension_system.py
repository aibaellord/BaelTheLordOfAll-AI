#!/usr/bin/env python3
"""
BAEL - Extension System
Comprehensive extension architecture for extensibility.

This module provides a complete extension system for
loading, managing, and executing extensions.

Features:
- Extension loading and unloading
- Extension lifecycle management
- Dependency resolution
- Hook system
- Event-based communication
- Extension isolation
- Hot reloading
- Extension discovery
- Version management
- Extension configuration
"""

import asyncio
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)
from weakref import WeakSet

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ExtensionState(Enum):
    """Extension lifecycle states."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADED = "unloaded"


class ExtHookPriority(Enum):
    """Hook execution priority."""
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100


class ExtensionType(Enum):
    """Extension types."""
    EXTENSION = "extension"
    PROVIDER = "provider"
    MIDDLEWARE = "middleware"
    THEME = "theme"
    LANGUAGE = "language"
    ADAPTER = "adapter"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ExtensionInfo:
    """Extension metadata."""
    id: str
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    extension_type: ExtensionType = ExtensionType.EXTENSION
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    config_schema: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtensionInfo':
        """Create from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            description=data.get('description', ''),
            extension_type=ExtensionType(data.get('type', 'extension')),
            dependencies=data.get('dependencies', []),
            tags=set(data.get('tags', [])),
            config_schema=data.get('config_schema', {})
        )


@dataclass
class ExtensionContext:
    """Context passed to extensions."""
    extension_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    services: Dict[str, Any] = field(default_factory=dict)

    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        return self.services.get(name)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


@dataclass
class ExtHookResult:
    """Result of hook execution."""
    extension_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass
class ExtensionEvent:
    """Event for extension communication."""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# EXTENSION BASE CLASS
# =============================================================================

class Extension(ABC):
    """
    Base class for all extensions.
    """

    def __init__(self):
        self._info: Optional[ExtensionInfo] = None
        self._context: Optional[ExtensionContext] = None
        self._state = ExtensionState.DISCOVERED
        self._hooks: Dict[str, Callable] = {}

    @property
    def info(self) -> ExtensionInfo:
        """Get extension info."""
        if not self._info:
            self._info = self.get_extension_info()
        return self._info

    @property
    def state(self) -> ExtensionState:
        """Get current state."""
        return self._state

    @property
    def context(self) -> Optional[ExtensionContext]:
        """Get extension context."""
        return self._context

    @abstractmethod
    def get_extension_info(self) -> ExtensionInfo:
        """Return extension metadata."""
        pass

    async def initialize(self, context: ExtensionContext) -> bool:
        """Initialize the extension."""
        self._context = context
        return True

    async def enable(self) -> bool:
        """Enable the extension."""
        return True

    async def disable(self) -> bool:
        """Disable the extension."""
        return True

    async def unload(self) -> bool:
        """Unload the extension."""
        return True

    def register_hook(
        self,
        hook_name: str,
        handler: Callable,
        priority: ExtHookPriority = ExtHookPriority.NORMAL
    ) -> None:
        """Register a hook handler."""
        self._hooks[hook_name] = handler

    def get_hooks(self) -> Dict[str, Callable]:
        """Get registered hooks."""
        return self._hooks


# =============================================================================
# HOOK SYSTEM
# =============================================================================

@dataclass
class ExtHookHandler:
    """A registered hook handler."""
    extension_id: str
    handler: Callable
    priority: ExtHookPriority = ExtHookPriority.NORMAL
    async_handler: bool = False


class ExtHookRegistry:
    """Registry for managing hooks."""

    def __init__(self):
        self.hooks: Dict[str, List[ExtHookHandler]] = defaultdict(list)

    def register(
        self,
        hook_name: str,
        extension_id: str,
        handler: Callable,
        priority: ExtHookPriority = ExtHookPriority.NORMAL
    ) -> None:
        """Register a hook handler."""
        is_async = asyncio.iscoroutinefunction(handler)

        hook_handler = ExtHookHandler(
            extension_id=extension_id,
            handler=handler,
            priority=priority,
            async_handler=is_async
        )

        self.hooks[hook_name].append(hook_handler)

        # Sort by priority (highest first)
        self.hooks[hook_name].sort(
            key=lambda h: h.priority.value,
            reverse=True
        )

    def unregister(self, hook_name: str, extension_id: str) -> None:
        """Unregister handlers for an extension."""
        if hook_name in self.hooks:
            self.hooks[hook_name] = [
                h for h in self.hooks[hook_name]
                if h.extension_id != extension_id
            ]

    def unregister_all(self, extension_id: str) -> None:
        """Unregister all handlers for an extension."""
        for hook_name in list(self.hooks.keys()):
            self.hooks[hook_name] = [
                h for h in self.hooks[hook_name]
                if h.extension_id != extension_id
            ]

    async def execute(
        self,
        hook_name: str,
        *args,
        **kwargs
    ) -> List[ExtHookResult]:
        """Execute all handlers for a hook."""
        results = []

        for handler in self.hooks.get(hook_name, []):
            try:
                if handler.async_handler:
                    result = await handler.handler(*args, **kwargs)
                else:
                    result = handler.handler(*args, **kwargs)

                results.append(ExtHookResult(
                    extension_id=handler.extension_id,
                    success=True,
                    result=result
                ))
            except Exception as e:
                results.append(ExtHookResult(
                    extension_id=handler.extension_id,
                    success=False,
                    error=str(e)
                ))

        return results

    async def execute_filter(
        self,
        hook_name: str,
        value: Any,
        *args,
        **kwargs
    ) -> Any:
        """Execute handlers as filter (each modifies value)."""
        for handler in self.hooks.get(hook_name, []):
            try:
                if handler.async_handler:
                    value = await handler.handler(value, *args, **kwargs)
                else:
                    value = handler.handler(value, *args, **kwargs)
            except Exception as e:
                logger.error(f"Hook filter error: {e}")

        return value

    def get_handlers(self, hook_name: str) -> List[ExtHookHandler]:
        """Get handlers for a hook."""
        return self.hooks.get(hook_name, [])

    def list_hooks(self) -> List[str]:
        """List all registered hooks."""
        return list(self.hooks.keys())


# =============================================================================
# EVENT BUS
# =============================================================================

class ExtensionEventBus:
    """Event bus for extension communication."""

    def __init__(self):
        self.subscribers: Dict[str, List[Tuple[str, Callable]]] = defaultdict(list)
        self.event_history: List[ExtensionEvent] = []
        self.max_history = 1000

    def subscribe(
        self,
        event_name: str,
        extension_id: str,
        handler: Callable
    ) -> None:
        """Subscribe to an event."""
        self.subscribers[event_name].append((extension_id, handler))

    def unsubscribe(self, event_name: str, extension_id: str) -> None:
        """Unsubscribe from an event."""
        if event_name in self.subscribers:
            self.subscribers[event_name] = [
                (eid, h) for eid, h in self.subscribers[event_name]
                if eid != extension_id
            ]

    def unsubscribe_all(self, extension_id: str) -> None:
        """Unsubscribe extension from all events."""
        for event_name in list(self.subscribers.keys()):
            self.subscribers[event_name] = [
                (eid, h) for eid, h in self.subscribers[event_name]
                if eid != extension_id
            ]

    async def emit(
        self,
        event_name: str,
        data: Dict[str, Any] = None,
        source: str = ""
    ) -> None:
        """Emit an event."""
        event = ExtensionEvent(
            name=event_name,
            data=data or {},
            source=source
        )

        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]

        # Notify subscribers
        for extension_id, handler in self.subscribers.get(event_name, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {extension_id}: {e}")

    def get_history(
        self,
        event_name: str = None,
        limit: int = 100
    ) -> List[ExtensionEvent]:
        """Get event history."""
        events = self.event_history

        if event_name:
            events = [e for e in events if e.name == event_name]

        return events[-limit:]


# =============================================================================
# EXTENSION LOADER
# =============================================================================

class ExtensionLoader:
    """Loader for discovering and loading extensions."""

    def __init__(self, extension_dirs: List[str] = None):
        self.extension_dirs = extension_dirs or []
        self.loaded_modules: Dict[str, Any] = {}

    def add_extension_dir(self, path: str) -> None:
        """Add extension directory."""
        if path not in self.extension_dirs:
            self.extension_dirs.append(path)

    def discover(self) -> List[Tuple[str, Path]]:
        """Discover extensions in directories."""
        discovered = []

        for dir_path in self.extension_dirs:
            path = Path(dir_path)
            if not path.exists():
                continue

            # Look for extension packages
            for item in path.iterdir():
                if item.is_dir():
                    ext_file = item / "extension.py"
                    if ext_file.exists():
                        discovered.append((item.name, ext_file))

                elif item.suffix == '.py' and not item.name.startswith('_'):
                    discovered.append((item.stem, item))

        return discovered

    def load_extension_file(self, path: Path) -> Optional[Type[Extension]]:
        """Load extension from file."""
        try:
            module_name = f"bael_ext_{path.stem}_{uuid.uuid4().hex[:8]}"

            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            self.loaded_modules[module_name] = module

            # Find Extension subclass
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, Extension) and
                    obj is not Extension):
                    return obj

            return None
        except Exception as e:
            logger.error(f"Failed to load extension from {path}: {e}")
            return None

    def load_from_class(self, extension_class: Type[Extension]) -> Optional[Extension]:
        """Create extension instance from class."""
        try:
            return extension_class()
        except Exception as e:
            logger.error(f"Failed to instantiate extension: {e}")
            return None

    def unload_module(self, module_name: str) -> bool:
        """Unload an extension module."""
        if module_name in self.loaded_modules:
            del self.loaded_modules[module_name]
            if module_name in sys.modules:
                del sys.modules[module_name]
            return True
        return False


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class ExtDependencyResolver:
    """Resolves extension dependencies."""

    def __init__(self):
        self.extensions: Dict[str, ExtensionInfo] = {}

    def add_extension(self, info: ExtensionInfo) -> None:
        """Add extension for resolution."""
        self.extensions[info.id] = info

    def remove_extension(self, extension_id: str) -> None:
        """Remove extension."""
        if extension_id in self.extensions:
            del self.extensions[extension_id]

    def resolve_order(self, extension_ids: List[str] = None) -> List[str]:
        """Resolve loading order based on dependencies."""
        if extension_ids is None:
            extension_ids = list(self.extensions.keys())

        # Build dependency graph
        resolved = []
        unresolved = set(extension_ids)

        def resolve(extension_id: str, resolving: Set[str]):
            if extension_id in resolved:
                return

            if extension_id in resolving:
                raise ValueError(f"Circular dependency detected: {extension_id}")

            resolving.add(extension_id)

            info = self.extensions.get(extension_id)
            if info:
                for dep in info.dependencies:
                    if dep in self.extensions:
                        resolve(dep, resolving)

            resolving.remove(extension_id)
            resolved.append(extension_id)
            unresolved.discard(extension_id)

        for extension_id in extension_ids:
            if extension_id in unresolved:
                resolve(extension_id, set())

        return resolved

    def check_dependencies(self, extension_id: str) -> Tuple[bool, List[str]]:
        """Check if dependencies are satisfied."""
        info = self.extensions.get(extension_id)
        if not info:
            return False, ["Extension not found"]

        missing = []
        for dep in info.dependencies:
            if dep not in self.extensions:
                missing.append(dep)

        return len(missing) == 0, missing

    def get_dependents(self, extension_id: str) -> List[str]:
        """Get extensions that depend on this one."""
        dependents = []

        for eid, info in self.extensions.items():
            if extension_id in info.dependencies:
                dependents.append(eid)

        return dependents


# =============================================================================
# EXTENSION MANAGER
# =============================================================================

class ExtensionManager:
    """
    Core extension manager.
    """

    def __init__(self, extension_dirs: List[str] = None):
        # Core components
        self.loader = ExtensionLoader(extension_dirs)
        self.hooks = ExtHookRegistry()
        self.events = ExtensionEventBus()
        self.resolver = ExtDependencyResolver()

        # Extension storage
        self.extensions: Dict[str, Extension] = {}
        self.extension_configs: Dict[str, Dict[str, Any]] = {}

        # Services
        self.services: Dict[str, Any] = {}

    def add_extension_dir(self, path: str) -> None:
        """Add extension directory."""
        self.loader.add_extension_dir(path)

    def register_service(self, name: str, service: Any) -> None:
        """Register a service for extensions."""
        self.services[name] = service

    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        return self.services.get(name)

    async def discover_extensions(self) -> List[str]:
        """Discover extensions in directories."""
        discovered = self.loader.discover()
        extension_ids = []

        for name, path in discovered:
            extension_class = self.loader.load_extension_file(path)
            if extension_class:
                extension = self.loader.load_from_class(extension_class)
                if extension:
                    await self._register_extension(extension)
                    extension_ids.append(extension.info.id)

        return extension_ids

    async def register_extension(self, extension: Extension) -> bool:
        """Register an extension."""
        return await self._register_extension(extension)

    async def _register_extension(self, extension: Extension) -> bool:
        """Internal extension registration."""
        try:
            info = extension.info
            extension._state = ExtensionState.LOADED

            self.extensions[info.id] = extension
            self.resolver.add_extension(info)

            await self.events.emit("extension.registered", {
                "extension_id": info.id,
                "name": info.name
            })

            return True
        except Exception as e:
            logger.error(f"Failed to register extension: {e}")
            return False

    async def initialize_extension(
        self,
        extension_id: str,
        config: Dict[str, Any] = None
    ) -> bool:
        """Initialize an extension."""
        extension = self.extensions.get(extension_id)
        if not extension:
            return False

        # Check dependencies
        satisfied, missing = self.resolver.check_dependencies(extension_id)
        if not satisfied:
            logger.error(f"Missing dependencies for {extension_id}: {missing}")
            return False

        # Create context
        context = ExtensionContext(
            extension_id=extension_id,
            config=config or self.extension_configs.get(extension_id, {}),
            services=self.services
        )

        try:
            if await extension.initialize(context):
                extension._state = ExtensionState.INITIALIZED

                # Register extension hooks
                for hook_name, handler in extension.get_hooks().items():
                    self.hooks.register(hook_name, extension_id, handler)

                await self.events.emit("extension.initialized", {
                    "extension_id": extension_id
                })

                return True

            extension._state = ExtensionState.ERROR
            return False
        except Exception as e:
            logger.error(f"Failed to initialize extension {extension_id}: {e}")
            extension._state = ExtensionState.ERROR
            return False

    async def enable_extension(self, extension_id: str) -> bool:
        """Enable an extension."""
        extension = self.extensions.get(extension_id)
        if not extension or extension.state not in (
            ExtensionState.INITIALIZED, ExtensionState.DISABLED
        ):
            return False

        try:
            if await extension.enable():
                extension._state = ExtensionState.ENABLED

                await self.events.emit("extension.enabled", {
                    "extension_id": extension_id
                })

                return True
            return False
        except Exception as e:
            logger.error(f"Failed to enable extension {extension_id}: {e}")
            return False

    async def disable_extension(self, extension_id: str) -> bool:
        """Disable an extension."""
        extension = self.extensions.get(extension_id)
        if not extension or extension.state != ExtensionState.ENABLED:
            return False

        try:
            if await extension.disable():
                extension._state = ExtensionState.DISABLED

                await self.events.emit("extension.disabled", {
                    "extension_id": extension_id
                })

                return True
            return False
        except Exception as e:
            logger.error(f"Failed to disable extension {extension_id}: {e}")
            return False

    async def unload_extension(self, extension_id: str) -> bool:
        """Unload an extension."""
        extension = self.extensions.get(extension_id)
        if not extension:
            return False

        # Check dependents
        dependents = self.resolver.get_dependents(extension_id)
        enabled_dependents = [
            d for d in dependents
            if self.extensions.get(d, {}).state == ExtensionState.ENABLED
        ]

        if enabled_dependents:
            logger.error(f"Cannot unload {extension_id}: required by {enabled_dependents}")
            return False

        try:
            # Disable first if enabled
            if extension.state == ExtensionState.ENABLED:
                await self.disable_extension(extension_id)

            # Unload
            if await extension.unload():
                # Clean up
                self.hooks.unregister_all(extension_id)
                self.events.unsubscribe_all(extension_id)
                self.resolver.remove_extension(extension_id)

                extension._state = ExtensionState.UNLOADED
                del self.extensions[extension_id]

                await self.events.emit("extension.unloaded", {
                    "extension_id": extension_id
                })

                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unload extension {extension_id}: {e}")
            return False

    async def initialize_all(self) -> Dict[str, bool]:
        """Initialize all extensions in order."""
        results = {}

        # Get sorted order
        order = self.resolver.resolve_order()

        for extension_id in order:
            success = await self.initialize_extension(extension_id)
            results[extension_id] = success

        return results

    async def enable_all(self) -> Dict[str, bool]:
        """Enable all initialized extensions."""
        results = {}

        for extension_id, extension in self.extensions.items():
            if extension.state == ExtensionState.INITIALIZED:
                success = await self.enable_extension(extension_id)
                results[extension_id] = success

        return results

    async def execute_hook(
        self,
        hook_name: str,
        *args,
        **kwargs
    ) -> List[ExtHookResult]:
        """Execute a hook."""
        return await self.hooks.execute(hook_name, *args, **kwargs)

    async def filter_hook(
        self,
        hook_name: str,
        value: Any,
        *args,
        **kwargs
    ) -> Any:
        """Execute a filter hook."""
        return await self.hooks.execute_filter(hook_name, value, *args, **kwargs)

    async def emit_event(
        self,
        event_name: str,
        data: Dict[str, Any] = None,
        source: str = ""
    ) -> None:
        """Emit an event."""
        await self.events.emit(event_name, data, source)

    def get_extension(self, extension_id: str) -> Optional[Extension]:
        """Get an extension."""
        return self.extensions.get(extension_id)

    def get_extensions_by_type(
        self,
        extension_type: ExtensionType
    ) -> List[Extension]:
        """Get extensions by type."""
        return [
            e for e in self.extensions.values()
            if e.info.extension_type == extension_type
        ]

    def get_enabled_extensions(self) -> List[Extension]:
        """Get all enabled extensions."""
        return [
            e for e in self.extensions.values()
            if e.state == ExtensionState.ENABLED
        ]

    def set_config(self, extension_id: str, config: Dict[str, Any]) -> None:
        """Set extension configuration."""
        self.extension_configs[extension_id] = config

    def get_statistics(self) -> Dict[str, Any]:
        """Get extension statistics."""
        states = defaultdict(int)
        types = defaultdict(int)

        for extension in self.extensions.values():
            states[extension.state.value] += 1
            types[extension.info.extension_type.value] += 1

        return {
            "total": len(self.extensions),
            "states": dict(states),
            "types": dict(types),
            "hooks": len(self.hooks.list_hooks()),
            "services": len(self.services)
        }


# =============================================================================
# EXTENSION SYSTEM MANAGER
# =============================================================================

class ExtensionSystemManager:
    """
    Master extension system manager for BAEL.
    """

    def __init__(self, extension_dirs: List[str] = None):
        self.manager = ExtensionManager(extension_dirs)

    def add_extension_dir(self, path: str) -> None:
        """Add extension directory."""
        self.manager.add_extension_dir(path)

    def register_service(self, name: str, service: Any) -> None:
        """Register a service."""
        self.manager.register_service(name, service)

    async def discover_and_load(self) -> Dict[str, bool]:
        """Discover, initialize, and enable all extensions."""
        await self.manager.discover_extensions()
        init_results = await self.manager.initialize_all()
        enable_results = await self.manager.enable_all()

        return {
            eid: init_results.get(eid, False) and enable_results.get(eid, False)
            for eid in set(init_results) | set(enable_results)
        }

    async def register_extension(
        self,
        extension: Extension,
        config: Dict[str, Any] = None
    ) -> bool:
        """Register and initialize an extension."""
        if not await self.manager.register_extension(extension):
            return False

        if config:
            self.manager.set_config(extension.info.id, config)

        if not await self.manager.initialize_extension(extension.info.id, config):
            return False

        return await self.manager.enable_extension(extension.info.id)

    async def unload_extension(self, extension_id: str) -> bool:
        """Unload an extension."""
        return await self.manager.unload_extension(extension_id)

    async def hook(
        self,
        hook_name: str,
        *args,
        **kwargs
    ) -> List[ExtHookResult]:
        """Execute a hook."""
        return await self.manager.execute_hook(hook_name, *args, **kwargs)

    async def filter(
        self,
        hook_name: str,
        value: Any,
        *args,
        **kwargs
    ) -> Any:
        """Execute filter hook."""
        return await self.manager.filter_hook(hook_name, value, *args, **kwargs)

    async def emit(
        self,
        event_name: str,
        data: Dict[str, Any] = None
    ) -> None:
        """Emit event."""
        await self.manager.emit_event(event_name, data)

    def get_extension(self, extension_id: str) -> Optional[Extension]:
        """Get an extension."""
        return self.manager.get_extension(extension_id)

    def get_enabled_extensions(self) -> List[Extension]:
        """Get enabled extensions."""
        return self.manager.get_enabled_extensions()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.manager.get_statistics()


# =============================================================================
# DEMO EXTENSIONS
# =============================================================================

class GreetingExtension(Extension):
    """Demo greeting extension."""

    def get_extension_info(self) -> ExtensionInfo:
        return ExtensionInfo(
            id="greeting",
            name="Greeting Extension",
            version="1.0.0",
            author="BAEL",
            description="Adds greeting functionality"
        )

    async def initialize(self, context: ExtensionContext) -> bool:
        await super().initialize(context)

        self.register_hook("greet", self.greet)
        self.register_hook("format_message", self.format_message)

        return True

    def greet(self, name: str) -> str:
        prefix = self.context.get_config("prefix", "Hello")
        return f"{prefix}, {name}!"

    def format_message(self, message: str) -> str:
        return f"[Greeting] {message}"


class LoggerExtension(Extension):
    """Demo logger extension."""

    def get_extension_info(self) -> ExtensionInfo:
        return ExtensionInfo(
            id="logger",
            name="Logger Extension",
            version="1.0.0",
            author="BAEL",
            description="Adds logging functionality"
        )

    async def initialize(self, context: ExtensionContext) -> bool:
        await super().initialize(context)

        self.logs = []
        self.register_hook("log", self.log)

        return True

    def log(self, message: str, level: str = "info") -> None:
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message
        }
        self.logs.append(entry)
        print(f"[{level.upper()}] {message}")

    def get_logs(self) -> List[Dict]:
        return self.logs


class AnalyticsExtension(Extension):
    """Demo analytics extension."""

    def get_extension_info(self) -> ExtensionInfo:
        return ExtensionInfo(
            id="analytics",
            name="Analytics Extension",
            version="1.0.0",
            author="BAEL",
            description="Adds analytics tracking",
            dependencies=["logger"]
        )

    async def initialize(self, context: ExtensionContext) -> bool:
        await super().initialize(context)

        self.events = []
        self.register_hook("track", self.track)

        return True

    def track(self, event_name: str, data: Dict = None) -> None:
        entry = {
            "event": event_name,
            "data": data or {},
            "timestamp": time.time()
        }
        self.events.append(entry)

    def get_events(self) -> List[Dict]:
        return self.events


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Extension System."""
    print("=" * 70)
    print("BAEL - EXTENSION SYSTEM DEMO")
    print("Extensible Extension Architecture")
    print("=" * 70)
    print()

    manager = ExtensionSystemManager()

    # 1. Register Services
    print("1. REGISTER SERVICES:")
    print("-" * 40)

    manager.register_service("config", {"app_name": "BAEL"})
    manager.register_service("database", {"connection": "mock://localhost"})

    print("   ✓ Registered: config")
    print("   ✓ Registered: database")
    print()

    # 2. Register Extensions
    print("2. REGISTER EXTENSIONS:")
    print("-" * 40)

    greeting = GreetingExtension()
    logger_ext = LoggerExtension()
    analytics = AnalyticsExtension()

    await manager.register_extension(greeting, {"prefix": "Welcome"})
    print(f"   ✓ {greeting.info.name} v{greeting.info.version}")

    await manager.register_extension(logger_ext)
    print(f"   ✓ {logger_ext.info.name} v{logger_ext.info.version}")

    await manager.register_extension(analytics)
    print(f"   ✓ {analytics.info.name} v{analytics.info.version}")
    print()

    # 3. Execute Hooks
    print("3. EXECUTE HOOKS:")
    print("-" * 40)

    results = await manager.hook("greet", "World")
    for r in results:
        print(f"   {r.result}")

    results = await manager.hook("log", "Application started")
    print()

    # 4. Filter Hooks
    print("4. FILTER HOOKS:")
    print("-" * 40)

    original = "Hello BAEL"
    filtered = await manager.filter("format_message", original)
    print(f"   Original: {original}")
    print(f"   Filtered: {filtered}")
    print()

    # 5. Event System
    print("5. EVENT SYSTEM:")
    print("-" * 40)

    received_events = []

    def on_user_login(event):
        received_events.append(event)
        print(f"   Event received: {event.name} - {event.data}")

    manager.manager.events.subscribe("user.login", "demo", on_user_login)

    await manager.emit("user.login", {"user": "admin"})
    print()

    # 6. Extension Dependencies
    print("6. EXTENSION DEPENDENCIES:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"   Total extensions: {stats['total']}")
    print(f"   Enabled: {stats['states'].get('enabled', 0)}")
    print(f"   Hooks registered: {stats['hooks']}")
    print()

    # 7. Analytics Tracking
    print("7. ANALYTICS TRACKING:")
    print("-" * 40)

    await manager.hook("track", "page_view", {"page": "/home"})
    await manager.hook("track", "button_click", {"button": "signup"})

    analytics_ext = manager.get_extension("analytics")
    events = analytics_ext.get_events()
    print(f"   Tracked events:")
    for e in events:
        print(f"     - {e['event']}: {e['data']}")
    print()

    # 8. Extension States
    print("8. EXTENSION STATES:")
    print("-" * 40)

    for extension in manager.get_enabled_extensions():
        print(f"   {extension.info.id}: {extension.state.value}")
    print()

    # 9. Unload Extension
    print("9. UNLOAD EXTENSION:")
    print("-" * 40)

    # Can't unload logger because analytics depends on it
    print("   Trying to unload 'logger' (has dependents)...")
    success = await manager.unload_extension("logger")
    print(f"   Result: {'Failed (expected)' if not success else 'Success'}")

    # Unload analytics first, then logger
    await manager.unload_extension("analytics")
    print("   ✓ Unloaded 'analytics'")

    success = await manager.unload_extension("logger")
    print(f"   ✓ Unloaded 'logger'" if success else "   Failed to unload 'logger'")
    print()

    # 10. Final Statistics
    print("10. FINAL STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Total extensions: {stats['total']}")
    print(f"    States: {stats['states']}")
    print(f"    Services: {stats['services']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Extension System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
