"""
BAEL Plugin Engine
==================

Extensible plugin system for dynamic capability loading.

Features:
- Plugin discovery and loading
- Dependency resolution
- Hot reloading
- Sandboxed execution
- Hook system for extensibility

"Every plugin is a new dimension of power." — Ba'el
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
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger("BAEL.Plugins")


# =============================================================================
# ENUMS
# =============================================================================

class PluginType(Enum):
    """Types of plugins."""
    CORE = "core"              # Core system extensions
    INTEGRATION = "integration"  # External integrations
    TOOL = "tool"              # Tools and utilities
    AGENT = "agent"            # Agent extensions
    WORKFLOW = "workflow"      # Workflow nodes
    UI = "ui"                  # UI components
    STORAGE = "storage"        # Storage backends
    COMMUNICATION = "communication"  # Communication channels


class PluginStatus(Enum):
    """Plugin status."""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"
    UNLOADED = "unloaded"


class PluginPriority(Enum):
    """Plugin execution priority."""
    LOWEST = 1
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100
    CRITICAL = 1000


class HookType(Enum):
    """Types of hooks."""
    # Lifecycle
    BEFORE_INIT = "before_init"
    AFTER_INIT = "after_init"
    BEFORE_SHUTDOWN = "before_shutdown"
    AFTER_SHUTDOWN = "after_shutdown"

    # Processing
    BEFORE_PROCESS = "before_process"
    AFTER_PROCESS = "after_process"
    ON_ERROR = "on_error"

    # Agents
    BEFORE_AGENT_RUN = "before_agent_run"
    AFTER_AGENT_RUN = "after_agent_run"

    # Workflows
    BEFORE_WORKFLOW = "before_workflow"
    AFTER_WORKFLOW = "after_workflow"

    # Custom
    CUSTOM = "custom"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PluginDependency:
    """A plugin dependency."""
    name: str
    version: Optional[str] = None
    optional: bool = False


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.TOOL
    dependencies: List[PluginDependency] = field(default_factory=list)
    python_requires: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    license: Optional[str] = None


@dataclass
class PluginConfig:
    """Plugin engine configuration."""
    plugins_dir: Path = field(default_factory=lambda: Path("plugins"))
    auto_discover: bool = True
    auto_load: bool = True
    sandbox_enabled: bool = True
    hot_reload: bool = False
    max_load_time_seconds: float = 30.0


@dataclass
class Hook:
    """A registered hook."""
    name: str
    hook_type: HookType
    callback: Callable
    plugin_id: Optional[str] = None
    priority: PluginPriority = PluginPriority.NORMAL
    async_callback: bool = False


# =============================================================================
# PLUGIN BASE CLASS
# =============================================================================

class Plugin(ABC):
    """Base class for all plugins."""

    # Override these in subclasses
    PLUGIN_ID: str = ""
    PLUGIN_NAME: str = ""
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_DESCRIPTION: str = ""
    PLUGIN_AUTHOR: str = ""
    PLUGIN_TYPE: PluginType = PluginType.TOOL
    PLUGIN_DEPENDENCIES: List[PluginDependency] = []

    def __init__(self):
        self.status = PluginStatus.LOADED
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"BAEL.Plugin.{self.PLUGIN_NAME}")

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id=self.PLUGIN_ID,
            name=self.PLUGIN_NAME,
            version=self.PLUGIN_VERSION,
            description=self.PLUGIN_DESCRIPTION,
            author=self.PLUGIN_AUTHOR,
            plugin_type=self.PLUGIN_TYPE,
            dependencies=self.PLUGIN_DEPENDENCIES
        )

    async def activate(self):
        """Activate the plugin. Override in subclasses."""
        self.status = PluginStatus.ACTIVE

    async def deactivate(self):
        """Deactivate the plugin. Override in subclasses."""
        self.status = PluginStatus.INACTIVE

    def configure(self, config: Dict[str, Any]):
        """Configure the plugin."""
        self.config = config

    def get_hooks(self) -> List[Tuple[HookType, Callable]]:
        """Get hooks provided by this plugin. Override in subclasses."""
        return []

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools provided by this plugin. Override in subclasses."""
        return []

    def get_commands(self) -> List[Dict[str, Any]]:
        """Get CLI commands provided by this plugin. Override in subclasses."""
        return []


# =============================================================================
# PLUGIN LOADER
# =============================================================================

class PluginLoader:
    """Loads plugins from various sources."""

    def __init__(self, config: PluginConfig):
        self.config = config
        self._loaded_modules: Dict[str, Any] = {}

    def discover(self, directory: Optional[Path] = None) -> List[Path]:
        """Discover plugin files in a directory."""
        plugins_dir = directory or self.config.plugins_dir

        if not plugins_dir.exists():
            plugins_dir.mkdir(parents=True, exist_ok=True)
            return []

        discovered = []

        # Look for plugin.py or plugin.json files
        for path in plugins_dir.rglob("plugin.py"):
            discovered.append(path)

        for path in plugins_dir.rglob("plugin.json"):
            discovered.append(path)

        # Also look for direct Python files
        for path in plugins_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            discovered.append(path)

        return discovered

    def load_from_file(self, path: Path) -> Optional[Plugin]:
        """Load a plugin from a file."""
        try:
            if path.suffix == ".json":
                return self._load_from_manifest(path)
            elif path.suffix == ".py":
                return self._load_from_python(path)
            else:
                logger.warning(f"Unknown plugin file type: {path}")
                return None

        except Exception as e:
            logger.error(f"Failed to load plugin from {path}: {e}")
            return None

    def _load_from_python(self, path: Path) -> Optional[Plugin]:
        """Load a plugin from a Python file."""
        module_name = f"bael_plugin_{path.stem}_{int(time.time())}"

        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        self._loaded_modules[module_name] = module

        # Find Plugin subclass in module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, Plugin) and
                obj is not Plugin):
                return obj()

        return None

    def _load_from_manifest(self, path: Path) -> Optional[Plugin]:
        """Load a plugin from a JSON manifest."""
        try:
            manifest = json.loads(path.read_text())

            # Look for main.py in same directory
            main_file = path.parent / manifest.get("main", "main.py")
            if main_file.exists():
                return self._load_from_python(main_file)

            # Create a dynamic plugin class
            class DynamicPlugin(Plugin):
                PLUGIN_ID = manifest.get("id", path.stem)
                PLUGIN_NAME = manifest.get("name", path.stem)
                PLUGIN_VERSION = manifest.get("version", "1.0.0")
                PLUGIN_DESCRIPTION = manifest.get("description", "")
                PLUGIN_AUTHOR = manifest.get("author", "")

            return DynamicPlugin()

        except Exception as e:
            logger.error(f"Failed to load manifest {path}: {e}")
            return None

    def unload(self, plugin_id: str):
        """Unload a plugin module."""
        modules_to_remove = [
            name for name in self._loaded_modules
            if plugin_id in name
        ]

        for name in modules_to_remove:
            if name in sys.modules:
                del sys.modules[name]
            del self._loaded_modules[name]


# =============================================================================
# PLUGIN REGISTRY
# =============================================================================

class PluginRegistry:
    """Registry for managing loaded plugins."""

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._by_type: Dict[PluginType, List[str]] = {}
        self._lock = threading.Lock()

    def register(self, plugin: Plugin):
        """Register a plugin."""
        with self._lock:
            plugin_id = plugin.PLUGIN_ID or plugin.PLUGIN_NAME
            self._plugins[plugin_id] = plugin

            plugin_type = plugin.PLUGIN_TYPE
            if plugin_type not in self._by_type:
                self._by_type[plugin_type] = []
            self._by_type[plugin_type].append(plugin_id)

            logger.info(f"Registered plugin: {plugin.PLUGIN_NAME} ({plugin_id})")

    def unregister(self, plugin_id: str):
        """Unregister a plugin."""
        with self._lock:
            if plugin_id in self._plugins:
                plugin = self._plugins[plugin_id]
                del self._plugins[plugin_id]

                plugin_type = plugin.PLUGIN_TYPE
                if plugin_type in self._by_type:
                    if plugin_id in self._by_type[plugin_type]:
                        self._by_type[plugin_type].remove(plugin_id)

    def get(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)

    def get_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get plugins by type."""
        plugin_ids = self._by_type.get(plugin_type, [])
        return [self._plugins[pid] for pid in plugin_ids if pid in self._plugins]

    def list(self) -> List[Plugin]:
        """List all plugins."""
        return list(self._plugins.values())

    def list_active(self) -> List[Plugin]:
        """List active plugins."""
        return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]

    def is_registered(self, plugin_id: str) -> bool:
        """Check if a plugin is registered."""
        return plugin_id in self._plugins


# =============================================================================
# HOOK MANAGER
# =============================================================================

class HookManager:
    """Manages plugin hooks."""

    def __init__(self):
        self._hooks: Dict[HookType, List[Hook]] = {}
        self._custom_hooks: Dict[str, List[Hook]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        hook_type: HookType,
        callback: Callable,
        plugin_id: Optional[str] = None,
        priority: PluginPriority = PluginPriority.NORMAL,
        name: Optional[str] = None
    ):
        """Register a hook."""
        hook = Hook(
            name=name or f"{hook_type.value}_{id(callback)}",
            hook_type=hook_type,
            callback=callback,
            plugin_id=plugin_id,
            priority=priority,
            async_callback=asyncio.iscoroutinefunction(callback)
        )

        with self._lock:
            if hook_type == HookType.CUSTOM:
                hook_name = name or "default"
                if hook_name not in self._custom_hooks:
                    self._custom_hooks[hook_name] = []
                self._custom_hooks[hook_name].append(hook)
                self._custom_hooks[hook_name].sort(key=lambda h: -h.priority.value)
            else:
                if hook_type not in self._hooks:
                    self._hooks[hook_type] = []
                self._hooks[hook_type].append(hook)
                self._hooks[hook_type].sort(key=lambda h: -h.priority.value)

    def unregister(self, hook_type: HookType, callback: Callable):
        """Unregister a hook."""
        with self._lock:
            if hook_type in self._hooks:
                self._hooks[hook_type] = [
                    h for h in self._hooks[hook_type]
                    if h.callback != callback
                ]

    def unregister_plugin(self, plugin_id: str):
        """Unregister all hooks for a plugin."""
        with self._lock:
            for hook_type in self._hooks:
                self._hooks[hook_type] = [
                    h for h in self._hooks[hook_type]
                    if h.plugin_id != plugin_id
                ]

            for hook_name in self._custom_hooks:
                self._custom_hooks[hook_name] = [
                    h for h in self._custom_hooks[hook_name]
                    if h.plugin_id != plugin_id
                ]

    async def trigger(
        self,
        hook_type: HookType,
        *args,
        custom_name: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """Trigger all hooks of a type."""
        if hook_type == HookType.CUSTOM:
            hooks = self._custom_hooks.get(custom_name or "default", [])
        else:
            hooks = self._hooks.get(hook_type, [])

        results = []

        for hook in hooks:
            try:
                if hook.async_callback:
                    result = await hook.callback(*args, **kwargs)
                else:
                    result = hook.callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook.name} error: {e}")
                if hook_type == HookType.ON_ERROR:
                    # Don't recurse on error hooks
                    pass
                else:
                    await self.trigger(HookType.ON_ERROR, e, hook=hook)

        return results

    def get_hooks(self, hook_type: HookType) -> List[Hook]:
        """Get all hooks of a type."""
        return self._hooks.get(hook_type, [])


# =============================================================================
# PLUGIN SANDBOX
# =============================================================================

class PluginSandbox:
    """Sandboxed execution environment for plugins."""

    def __init__(self):
        self._allowed_modules: Set[str] = {
            "json", "re", "datetime", "collections",
            "itertools", "functools", "hashlib", "base64",
            "urllib.parse", "math", "random", "time"
        }
        self._restricted_attrs: Set[str] = {
            "__import__", "eval", "exec", "compile",
            "open", "file", "input", "raw_input"
        }

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """Execute code in sandbox."""
        # Create restricted globals
        safe_globals = {
            "__builtins__": self._safe_builtins(),
            "json": __import__("json"),
            "re": __import__("re"),
            "datetime": __import__("datetime"),
            "math": __import__("math"),
        }

        if context:
            safe_globals.update(context)

        # Execute with timeout
        result = {"value": None, "error": None}

        def run():
            try:
                compiled = compile(code, "<plugin>", "exec")
                exec(compiled, safe_globals)
                result["value"] = safe_globals.get("result")
            except Exception as e:
                result["error"] = str(e)

        thread = threading.Thread(target=run)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"Plugin execution timed out after {timeout}s")

        if result["error"]:
            raise RuntimeError(f"Plugin error: {result['error']}")

        return result["value"]

    def _safe_builtins(self) -> Dict[str, Any]:
        """Get safe builtins."""
        import builtins

        safe = {}
        allowed = [
            "abs", "all", "any", "bool", "dict", "dir", "enumerate",
            "filter", "float", "format", "frozenset", "getattr", "hasattr",
            "hash", "hex", "id", "int", "isinstance", "issubclass", "iter",
            "len", "list", "map", "max", "min", "next", "oct", "ord",
            "pow", "print", "range", "repr", "reversed", "round", "set",
            "slice", "sorted", "str", "sum", "tuple", "type", "zip"
        ]

        for name in allowed:
            if hasattr(builtins, name):
                safe[name] = getattr(builtins, name)

        safe["True"] = True
        safe["False"] = False
        safe["None"] = None

        return safe


# =============================================================================
# PLUGIN ENGINE
# =============================================================================

class PluginEngine:
    """Main plugin engine."""

    def __init__(self, config: Optional[PluginConfig] = None):
        self.config = config or PluginConfig()
        self.config.plugins_dir.mkdir(parents=True, exist_ok=True)

        self.loader = PluginLoader(self.config)
        self.registry = PluginRegistry()
        self.hooks = HookManager()
        self.sandbox = PluginSandbox()

        self._running = False

    async def start(self):
        """Start the plugin engine."""
        self._running = True

        # Trigger init hooks
        await self.hooks.trigger(HookType.BEFORE_INIT)

        if self.config.auto_discover:
            await self.discover_all()

        if self.config.auto_load:
            await self.load_all()

        await self.hooks.trigger(HookType.AFTER_INIT)

        logger.info(f"Plugin engine started with {len(self.registry.list())} plugins")

    async def stop(self):
        """Stop the plugin engine."""
        await self.hooks.trigger(HookType.BEFORE_SHUTDOWN)

        # Deactivate all plugins
        for plugin in self.registry.list_active():
            await self.deactivate(plugin.PLUGIN_ID)

        await self.hooks.trigger(HookType.AFTER_SHUTDOWN)

        self._running = False
        logger.info("Plugin engine stopped")

    async def discover_all(self) -> List[Path]:
        """Discover all plugins."""
        return self.loader.discover()

    async def load_all(self):
        """Load all discovered plugins."""
        paths = await self.discover_all()

        for path in paths:
            await self.load(path)

    async def load(self, source: Union[str, Path]) -> Optional[Plugin]:
        """Load a plugin from a source."""
        path = Path(source) if isinstance(source, str) else source

        if not path.exists():
            logger.error(f"Plugin source not found: {path}")
            return None

        plugin = self.loader.load_from_file(path)

        if plugin:
            # Check dependencies
            for dep in plugin.PLUGIN_DEPENDENCIES:
                if not dep.optional and not self.registry.is_registered(dep.name):
                    logger.error(f"Plugin {plugin.PLUGIN_NAME} missing dependency: {dep.name}")
                    return None

            self.registry.register(plugin)

            # Register hooks from plugin
            for hook_type, callback in plugin.get_hooks():
                self.hooks.register(hook_type, callback, plugin.PLUGIN_ID)

            return plugin

        return None

    async def unload(self, plugin_id: str):
        """Unload a plugin."""
        plugin = self.registry.get(plugin_id)

        if plugin:
            if plugin.status == PluginStatus.ACTIVE:
                await self.deactivate(plugin_id)

            self.hooks.unregister_plugin(plugin_id)
            self.registry.unregister(plugin_id)
            self.loader.unload(plugin_id)

            logger.info(f"Unloaded plugin: {plugin_id}")

    async def activate(self, plugin_id: str):
        """Activate a plugin."""
        plugin = self.registry.get(plugin_id)

        if plugin and plugin.status != PluginStatus.ACTIVE:
            try:
                await plugin.activate()
                logger.info(f"Activated plugin: {plugin_id}")
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                logger.error(f"Failed to activate plugin {plugin_id}: {e}")

    async def deactivate(self, plugin_id: str):
        """Deactivate a plugin."""
        plugin = self.registry.get(plugin_id)

        if plugin and plugin.status == PluginStatus.ACTIVE:
            try:
                await plugin.deactivate()
                logger.info(f"Deactivated plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self.registry.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins."""
        return [
            {
                "id": p.PLUGIN_ID,
                "name": p.PLUGIN_NAME,
                "version": p.PLUGIN_VERSION,
                "type": p.PLUGIN_TYPE.value,
                "status": p.status.value,
                "description": p.PLUGIN_DESCRIPTION
            }
            for p in self.registry.list()
        ]

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from plugins."""
        tools = []
        for plugin in self.registry.list_active():
            for tool in plugin.get_tools():
                tool["plugin_id"] = plugin.PLUGIN_ID
                tools.append(tool)
        return tools

    def get_commands(self) -> List[Dict[str, Any]]:
        """Get all commands from plugins."""
        commands = []
        for plugin in self.registry.list_active():
            for cmd in plugin.get_commands():
                cmd["plugin_id"] = plugin.PLUGIN_ID
                commands.append(cmd)
        return commands

    async def trigger_hook(self, hook_type: HookType, *args, **kwargs) -> List[Any]:
        """Trigger a hook."""
        return await self.hooks.trigger(hook_type, *args, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        """Get plugin engine status."""
        plugins = self.registry.list()

        return {
            "running": self._running,
            "plugins_dir": str(self.config.plugins_dir),
            "total_plugins": len(plugins),
            "active_plugins": len([p for p in plugins if p.status == PluginStatus.ACTIVE]),
            "by_type": {
                pt.value: len(self.registry.get_by_type(pt))
                for pt in PluginType
            }
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

plugin_engine = PluginEngine()
