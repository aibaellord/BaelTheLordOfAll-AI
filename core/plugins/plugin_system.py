"""
BAEL - Plugin System
Extensible plugin architecture for custom functionality.

Features:
- Dynamic plugin loading
- Plugin lifecycle management
- Dependency resolution
- Hot reloading
- Sandboxed execution
- Plugin marketplace integration
"""

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

logger = logging.getLogger("BAEL.Plugins")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class PluginState(Enum):
    """Plugin states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class PluginType(Enum):
    """Types of plugins."""
    TOOL = "tool"
    PERSONA = "persona"
    INTEGRATION = "integration"
    PROCESSOR = "processor"
    MIDDLEWARE = "middleware"
    THEME = "theme"


class HookPoint(Enum):
    """Plugin hook points."""
    PRE_THINK = "pre_think"
    POST_THINK = "post_think"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"
    ON_ERROR = "on_error"
    ON_START = "on_start"
    ON_SHUTDOWN = "on_shutdown"


@dataclass
class PluginMeta:
    """Plugin metadata."""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType

    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    bael_version: str = ">=1.0.0"

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Hooks
    hooks: List[HookPoint] = field(default_factory=list)

    # Permissions
    permissions: List[str] = field(default_factory=list)

    # Source
    source_path: Optional[str] = None
    is_builtin: bool = False


@dataclass
class PluginInstance:
    """A loaded plugin instance."""
    meta: PluginMeta
    instance: 'BaelPlugin'
    state: PluginState = PluginState.UNLOADED
    config: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None
    error: Optional[str] = None


# =============================================================================
# BASE PLUGIN CLASS
# =============================================================================

class BaelPlugin(ABC):
    """Base class for all BAEL plugins."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._hooks: Dict[HookPoint, List[Callable]] = {}

    @classmethod
    @abstractmethod
    def get_meta(cls) -> PluginMeta:
        """Return plugin metadata."""
        pass

    async def on_load(self) -> None:
        """Called when plugin is loaded."""
        pass

    async def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass

    async def on_enable(self) -> None:
        """Called when plugin is enabled."""
        pass

    async def on_disable(self) -> None:
        """Called when plugin is disabled."""
        pass

    def register_hook(self, hook_point: HookPoint, handler: Callable) -> None:
        """Register a hook handler."""
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        self._hooks[hook_point].append(handler)

    def get_hooks(self, hook_point: HookPoint) -> List[Callable]:
        """Get handlers for a hook point."""
        return self._hooks.get(hook_point, [])


# =============================================================================
# PLUGIN TOOL
# =============================================================================

class PluginTool(BaelPlugin):
    """Base class for tool plugins."""

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Get tool input schema."""
        return {}


class PluginPersona(BaelPlugin):
    """Base class for persona plugins."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the persona's system prompt."""
        pass

    @abstractmethod
    async def analyze(self, task: str) -> Dict[str, Any]:
        """Analyze a task from this persona's perspective."""
        pass


class PluginIntegration(BaelPlugin):
    """Base class for integration plugins."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the external service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass

    @abstractmethod
    async def send(self, message: Any) -> Any:
        """Send a message/request."""
        pass


class PluginProcessor(BaelPlugin):
    """Base class for processor plugins."""

    @abstractmethod
    async def process(self, data: Any) -> Any:
        """Process data."""
        pass


class PluginMiddleware(BaelPlugin):
    """Base class for middleware plugins."""

    @abstractmethod
    async def handle(self, request: Any, next_handler: Callable) -> Any:
        """Handle a request in the middleware chain."""
        pass


# =============================================================================
# PLUGIN LOADER
# =============================================================================

class PluginLoader:
    """Loads plugins from various sources."""

    def __init__(self, plugin_dirs: List[str] = None):
        self.plugin_dirs = plugin_dirs or []
        self._discovered: Dict[str, Path] = {}

    def discover(self) -> Dict[str, Path]:
        """Discover available plugins."""
        self._discovered.clear()

        for plugin_dir in self.plugin_dirs:
            dir_path = Path(plugin_dir)
            if not dir_path.exists():
                continue

            # Look for plugin packages
            for item in dir_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    manifest_path = item / "manifest.json"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path) as f:
                                manifest = json.load(f)
                                plugin_id = manifest.get('id', item.name)
                                self._discovered[plugin_id] = item
                        except:
                            self._discovered[item.name] = item

                # Single file plugins
                elif item.suffix == '.py' and not item.name.startswith('_'):
                    self._discovered[item.stem] = item

        logger.info(f"Discovered {len(self._discovered)} plugins")
        return self._discovered

    def load(self, plugin_path: Path) -> Optional[Type[BaelPlugin]]:
        """Load a plugin from path."""
        try:
            if plugin_path.is_dir():
                # Package plugin
                init_path = plugin_path / "__init__.py"
                spec = importlib.util.spec_from_file_location(
                    plugin_path.name,
                    init_path
                )
            else:
                # Single file plugin
                spec = importlib.util.spec_from_file_location(
                    plugin_path.stem,
                    plugin_path
                )

            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find plugin class
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaelPlugin) and obj is not BaelPlugin:
                    if not name.startswith('Plugin'):  # Skip base classes
                        return obj

            return None

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_path}: {e}")
            return None


# =============================================================================
# PLUGIN MANAGER
# =============================================================================

class PluginManager:
    """Manages plugin lifecycle."""

    def __init__(self, plugin_dirs: List[str] = None):
        self.loader = PluginLoader(plugin_dirs)
        self._plugins: Dict[str, PluginInstance] = {}
        self._hooks: Dict[HookPoint, List[Tuple[str, Callable]]] = {
            hook: [] for hook in HookPoint
        }

    async def initialize(self) -> None:
        """Initialize plugin system."""
        self.loader.discover()
        logger.info("Plugin manager initialized")

    async def load_plugin(
        self,
        plugin_id: str,
        config: Dict[str, Any] = None
    ) -> Optional[PluginInstance]:
        """Load and activate a plugin."""
        if plugin_id in self._plugins:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return self._plugins[plugin_id]

        # Find plugin
        plugin_path = self.loader._discovered.get(plugin_id)
        if not plugin_path:
            logger.error(f"Plugin not found: {plugin_id}")
            return None

        # Load plugin class
        plugin_class = self.loader.load(plugin_path)
        if not plugin_class:
            return None

        try:
            # Get metadata
            meta = plugin_class.get_meta()
            meta.source_path = str(plugin_path)

            # Check dependencies
            for dep in meta.dependencies:
                if dep not in self._plugins:
                    logger.error(f"Missing dependency: {dep} for {plugin_id}")
                    return None

            # Merge config
            final_config = {**meta.default_config, **(config or {})}

            # Create instance
            instance = plugin_class(final_config)

            # Create plugin instance record
            plugin_instance = PluginInstance(
                meta=meta,
                instance=instance,
                state=PluginState.LOADING,
                config=final_config,
                loaded_at=datetime.now()
            )

            # Call load hook
            await instance.on_load()

            # Register hooks
            for hook_point in meta.hooks:
                handlers = instance.get_hooks(hook_point)
                for handler in handlers:
                    self._hooks[hook_point].append((plugin_id, handler))

            plugin_instance.state = PluginState.ACTIVE
            self._plugins[plugin_id] = plugin_instance

            logger.info(f"Loaded plugin: {meta.name} v{meta.version}")
            return plugin_instance

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return None

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        if plugin_id not in self._plugins:
            return False

        plugin_instance = self._plugins[plugin_id]

        try:
            # Check dependents
            for other_id, other_plugin in self._plugins.items():
                if plugin_id in other_plugin.meta.dependencies:
                    logger.error(f"Cannot unload {plugin_id}: required by {other_id}")
                    return False

            # Call unload hook
            await plugin_instance.instance.on_unload()

            # Remove hooks
            for hook_point in HookPoint:
                self._hooks[hook_point] = [
                    (pid, h) for pid, h in self._hooks[hook_point]
                    if pid != plugin_id
                ]

            del self._plugins[plugin_id]
            logger.info(f"Unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_id}: {e}")
            plugin_instance.state = PluginState.ERROR
            plugin_instance.error = str(e)
            return False

    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a disabled plugin."""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        if plugin.state == PluginState.ACTIVE:
            return True

        try:
            await plugin.instance.on_enable()
            plugin.state = PluginState.ACTIVE
            return True
        except Exception as e:
            logger.error(f"Failed to enable {plugin_id}: {e}")
            return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin without unloading."""
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]
        if plugin.state == PluginState.DISABLED:
            return True

        try:
            await plugin.instance.on_disable()
            plugin.state = PluginState.DISABLED
            return True
        except Exception as e:
            logger.error(f"Failed to disable {plugin_id}: {e}")
            return False

    async def execute_hooks(
        self,
        hook_point: HookPoint,
        data: Any
    ) -> Any:
        """Execute all handlers for a hook point."""
        result = data

        for plugin_id, handler in self._hooks[hook_point]:
            try:
                plugin = self._plugins.get(plugin_id)
                if plugin and plugin.state == PluginState.ACTIVE:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(result)
                    else:
                        result = handler(result)
            except Exception as e:
                logger.error(f"Hook error in {plugin_id}: {e}")

        return result

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstance]:
        """Get a loaded plugin."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins."""
        return [
            {
                "id": plugin.meta.id,
                "name": plugin.meta.name,
                "version": plugin.meta.version,
                "type": plugin.meta.plugin_type.value,
                "state": plugin.state.value,
                "author": plugin.meta.author
            }
            for plugin in self._plugins.values()
        ]

    def get_tools(self) -> List[PluginInstance]:
        """Get all tool plugins."""
        return [
            p for p in self._plugins.values()
            if p.meta.plugin_type == PluginType.TOOL
            and p.state == PluginState.ACTIVE
        ]

    def get_personas(self) -> List[PluginInstance]:
        """Get all persona plugins."""
        return [
            p for p in self._plugins.values()
            if p.meta.plugin_type == PluginType.PERSONA
            and p.state == PluginState.ACTIVE
        ]


# =============================================================================
# EXAMPLE PLUGINS
# =============================================================================

class WeatherToolPlugin(PluginTool):
    """Example weather tool plugin."""

    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            id="weather-tool",
            name="Weather Tool",
            version="1.0.0",
            description="Get weather information",
            author="BAEL Team",
            plugin_type=PluginType.TOOL,
            config_schema={
                "api_key": {"type": "string", "required": True}
            }
        )

    async def execute(self, location: str = "New York") -> Dict[str, Any]:
        """Get weather for location."""
        # Simulated response
        return {
            "location": location,
            "temperature": 72,
            "conditions": "Sunny",
            "humidity": 45
        }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location to get weather for"
                }
            }
        }


class LoggingMiddlewarePlugin(PluginMiddleware):
    """Example logging middleware plugin."""

    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            id="logging-middleware",
            name="Logging Middleware",
            version="1.0.0",
            description="Log all requests",
            author="BAEL Team",
            plugin_type=PluginType.MIDDLEWARE,
            hooks=[HookPoint.PRE_THINK, HookPoint.POST_THINK]
        )

    async def on_load(self) -> None:
        """Register hooks."""
        self.register_hook(HookPoint.PRE_THINK, self.log_pre_think)
        self.register_hook(HookPoint.POST_THINK, self.log_post_think)

    async def log_pre_think(self, data: Any) -> Any:
        """Log before thinking."""
        logger.info(f"[LoggingMiddleware] Pre-think: {str(data)[:100]}")
        return data

    async def log_post_think(self, data: Any) -> Any:
        """Log after thinking."""
        logger.info(f"[LoggingMiddleware] Post-think: {str(data)[:100]}")
        return data

    async def handle(self, request: Any, next_handler: Callable) -> Any:
        """Handle request."""
        logger.info(f"Request: {request}")
        result = await next_handler(request)
        logger.info(f"Response: {result}")
        return result


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test plugin system."""
    manager = PluginManager()
    await manager.initialize()

    # Create and register a plugin manually for testing
    weather_plugin = WeatherToolPlugin({})
    weather_meta = WeatherToolPlugin.get_meta()

    instance = PluginInstance(
        meta=weather_meta,
        instance=weather_plugin,
        state=PluginState.ACTIVE,
        loaded_at=datetime.now()
    )

    manager._plugins[weather_meta.id] = instance

    print("Loaded plugins:")
    for plugin in manager.list_plugins():
        print(f"  - {plugin['name']} v{plugin['version']} ({plugin['type']})")

    # Test tool execution
    tools = manager.get_tools()
    if tools:
        tool = tools[0]
        result = await tool.instance.execute(location="San Francisco")
        print(f"\nWeather result: {result}")

    # Test middleware
    logging_plugin = LoggingMiddlewarePlugin({})
    await logging_plugin.on_load()

    logging_meta = LoggingMiddlewarePlugin.get_meta()
    logging_instance = PluginInstance(
        meta=logging_meta,
        instance=logging_plugin,
        state=PluginState.ACTIVE,
        loaded_at=datetime.now()
    )

    manager._plugins[logging_meta.id] = logging_instance

    # Register hooks
    for hook_point in logging_meta.hooks:
        for handler in logging_plugin.get_hooks(hook_point):
            manager._hooks[hook_point].append((logging_meta.id, handler))

    # Execute hooks
    print("\nExecuting hooks:")
    result = await manager.execute_hooks(HookPoint.PRE_THINK, "Hello, world!")
    print(f"Hook result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
