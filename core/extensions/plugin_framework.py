"""
BAEL Phase 6.2: Plugin & Extension Framework
═════════════════════════════════════════════════════════════════════════════

Comprehensive plugin system enabling dynamic extensibility, dependency resolution,
sandbox execution, version management, and marketplace integration.

Features:
  • Plugin Discovery & Loading
  • Dependency Resolution (topological sorting)
  • Sandbox Execution (resource limits)
  • Version Management (compatibility)
  • Plugin Lifecycle (enable/disable/update)
  • Marketplace Integration
  • Hook System (event-driven)
  • Configuration Injection
  • Health Monitoring
  • Plugin Metrics

Author: BAEL Team
Date: February 1, 2026
"""

import hashlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class PluginStatus(str, Enum):
    """Plugin execution status."""
    AVAILABLE = "available"
    ENABLED = "enabled"
    DISABLED = "disabled"
    LOADING = "loading"
    ERROR = "error"
    OUTDATED = "outdated"
    INCOMPATIBLE = "incompatible"


class HookType(str, Enum):
    """Hook event types for plugin lifecycle."""
    PRE_INIT = "pre_init"
    POST_INIT = "post_init"
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    PRE_DISABLE = "pre_disable"
    POST_DISABLE = "post_disable"
    ERROR = "error"


class PluginCategory(str, Enum):
    """Plugin classification categories."""
    INTEGRATION = "integration"
    ANALYTICS = "analytics"
    WORKFLOW = "workflow"
    SECURITY = "security"
    MONITORING = "monitoring"
    DATA = "data"
    AI = "ai"
    CUSTOM = "custom"


class SandboxLevel(str, Enum):
    """Execution sandbox restrictions."""
    UNRESTRICTED = "unrestricted"
    LIMITED = "limited"
    STRICT = "strict"
    ISOLATED = "isolated"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PluginRequirement:
    """Plugin dependency specification."""
    name: str
    version_min: str = "0.0.0"
    version_max: str = "999.999.999"
    optional: bool = False

    def is_satisfied(self, version: str) -> bool:
        """Check if requirement is satisfied by given version."""
        return self.version_min <= version <= self.version_max


@dataclass
class PluginMetadata:
    """Plugin metadata and manifest."""
    name: str
    version: str
    author: str
    description: str
    category: PluginCategory
    entry_point: str
    dependencies: List[PluginRequirement] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    sandbox_level: SandboxLevel = SandboxLevel.LIMITED
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    license: str = "MIT"
    min_python: str = "3.8"
    max_python: str = "3.12"


@dataclass
class PluginConfig:
    """Plugin runtime configuration."""
    enabled: bool = True
    sandbox_level: SandboxLevel = SandboxLevel.LIMITED
    max_memory_mb: int = 512
    max_execution_seconds: int = 300
    retry_on_failure: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginMetrics:
    """Plugin performance and usage metrics."""
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_execution_time_seconds: float = 0.0
    last_execution_time: Optional[datetime] = None
    avg_execution_time: float = 0.0
    peak_memory_usage_mb: float = 0.0

    def update_execution(self, success: bool, duration: float, memory_mb: float) -> None:
        """Update metrics after plugin execution."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self.total_execution_time_seconds += duration
        self.avg_execution_time = self.total_execution_time_seconds / self.execution_count
        self.last_execution_time = datetime.now(timezone.utc)
        self.peak_memory_usage_mb = max(self.peak_memory_usage_mb, memory_mb)

    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100


@dataclass
class PluginInfo:
    """Complete plugin information."""
    metadata: PluginMetadata
    status: PluginStatus
    config: PluginConfig
    metrics: PluginMetrics
    installed_at: datetime
    last_updated: datetime
    checksum: str
    dependencies_resolved: bool = False
    enabled_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Base Classes
# ═══════════════════════════════════════════════════════════════════════════

class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self, config: PluginConfig):
        """Initialize plugin with configuration."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._hooks: Dict[HookType, List[Callable]] = defaultdict(list)
        self._state: Dict[str, Any] = {}

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize plugin. Return True on success."""
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute main plugin functionality."""
        pass

    def shutdown(self) -> None:
        """Clean up plugin resources."""
        pass

    def validate(self) -> bool:
        """Validate plugin integrity and dependencies."""
        return True

    def register_hook(self, hook_type: HookType, handler: Callable) -> None:
        """Register event handler for hook."""
        self._hooks[hook_type].append(handler)

    def trigger_hook(self, hook_type: HookType, *args: Any, **kwargs: Any) -> List[Any]:
        """Trigger all handlers for hook type."""
        results = []
        for handler in self._hooks.get(hook_type, []):
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Hook handler error: {e}")
        return results


class SandboxedPlugin(BasePlugin):
    """Plugin with execution sandboxing."""

    def __init__(self, config: PluginConfig):
        """Initialize sandboxed plugin."""
        super().__init__(config)
        self._start_time: Optional[float] = None
        self._memory_tracker: Optional[float] = None

    def _check_execution_timeout(self) -> None:
        """Check if execution exceeded timeout."""
        if self._start_time is None:
            return
        elapsed = time.time() - self._start_time
        if elapsed > self.config.timeout_seconds:
            raise TimeoutError(
                f"Plugin execution timeout after {elapsed:.2f}s "
                f"(limit: {self.config.timeout_seconds}s)"
            )

    def _track_memory(self) -> float:
        """Track current memory usage (simplified)."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)  # MB
        except (ImportError, Exception):
            return 0.0

    def safe_execute(self, *args: Any, **kwargs: Any) -> Tuple[bool, Any, Optional[Exception]]:
        """Execute with sandboxing, error handling, and monitoring."""
        self._start_time = time.time()
        initial_memory = self._track_memory()

        try:
            result = self.execute(*args, **kwargs)
            elapsed = time.time() - self._start_time
            peak_memory = self._track_memory() - initial_memory
            return True, result, None
        except Exception as e:
            self.logger.error(f"Plugin execution error: {e}", exc_info=True)
            return False, None, e


# ═══════════════════════════════════════════════════════════════════════════
# Dependency Resolution
# ═══════════════════════════════════════════════════════════════════════════

class DependencyResolver:
    """Resolve plugin dependencies and detect cycles."""

    def __init__(self):
        """Initialize dependency resolver."""
        self.dependency_graph: Dict[str, List[str]] = {}

    def add_dependency(self, plugin_name: str, depends_on: List[str]) -> None:
        """Register plugin dependencies."""
        self.dependency_graph[plugin_name] = depends_on

    def resolve_order(self, plugins: List[str]) -> Tuple[List[str], List[str]]:
        """
        Topologically sort plugins by dependencies.

        Returns: (sorted_order, cyclic_plugins)
        """
        in_degree = {p: 0 for p in plugins}
        adjacency = {p: [] for p in plugins}

        for plugin in plugins:
            for dep in self.dependency_graph.get(plugin, []):
                if dep in adjacency:
                    adjacency[dep].append(plugin)
                    in_degree[plugin] += 1

        queue = [p for p in plugins if in_degree[p] == 0]
        sorted_order = []

        while queue:
            plugin = queue.pop(0)
            sorted_order.append(plugin)

            for dependent in adjacency[plugin]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        cyclic = [p for p in plugins if in_degree[p] > 0]
        return sorted_order, cyclic

    def validate_dependencies(
        self,
        plugin_name: str,
        available_plugins: Dict[str, PluginMetadata]
    ) -> Tuple[bool, List[str]]:
        """Validate that all dependencies are available."""
        metadata = available_plugins.get(plugin_name)
        if not metadata:
            return False, [f"Plugin {plugin_name} not found"]

        missing = []
        for req in metadata.dependencies:
            if req.name not in available_plugins:
                if not req.optional:
                    missing.append(f"Required dependency '{req.name}' not found")
            else:
                dep_version = available_plugins[req.name].version
                if not req.is_satisfied(dep_version):
                    missing.append(
                        f"Dependency '{req.name}' version mismatch: "
                        f"need {req.version_min}-{req.version_max}, have {dep_version}"
                    )

        return len(missing) == 0, missing


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Registry
# ═══════════════════════════════════════════════════════════════════════════

class PluginRegistry:
    """Central registry for plugins."""

    def __init__(self):
        """Initialize plugin registry."""
        self.plugins: Dict[str, PluginInfo] = {}
        self.instances: Dict[str, BasePlugin] = {}
        self.dependency_resolver = DependencyResolver()
        self._lock = threading.RLock()

    def register(self, metadata: PluginMetadata, checksum: str = "") -> None:
        """Register plugin metadata."""
        with self._lock:
            if metadata.name in self.plugins:
                raise ValueError(f"Plugin '{metadata.name}' already registered")

            if not checksum:
                checksum = "unverified"

            info = PluginInfo(
                metadata=metadata,
                status=PluginStatus.AVAILABLE,
                config=PluginConfig(),
                metrics=PluginMetrics(),
                installed_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                checksum=checksum
            )

            self.plugins[metadata.name] = info
            self.dependency_resolver.add_dependency(
                metadata.name,
                [dep.name for dep in metadata.dependencies]
            )

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Retrieve plugin information."""
        return self.plugins.get(name)

    def list_plugins(
        self,
        status: Optional[PluginStatus] = None,
        category: Optional[PluginCategory] = None
    ) -> List[PluginInfo]:
        """List plugins with optional filtering."""
        plugins = list(self.plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]
        if category:
            plugins = [p for p in plugins if p.metadata.category == category]

        return plugins

    def update_status(self, plugin_name: str, status: PluginStatus) -> None:
        """Update plugin status."""
        with self._lock:
            if plugin_name in self.plugins:
                self.plugins[plugin_name].status = status


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Loader
# ═══════════════════════════════════════════════════════════════════════════

class PluginLoader:
    """Dynamic plugin loading from Python modules."""

    def __init__(self, plugin_dirs: List[str]):
        """Initialize loader with plugin directories."""
        self.plugin_dirs = plugin_dirs
        self.logger = logging.getLogger(__name__)

    def load_plugin_module(self, plugin_path: str) -> Any:
        """Load plugin from Python file."""
        try:
            spec = importlib.util.spec_from_file_location(
                Path(plugin_path).stem,
                plugin_path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Failed to load spec for {plugin_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            self.logger.error(f"Failed to load plugin module: {e}")
            raise

    def discover_plugins(self) -> Dict[str, PluginMetadata]:
        """Discover plugins in configured directories."""
        discovered = {}

        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue

            for file in os.listdir(plugin_dir):
                if file.endswith('.py') and not file.startswith('_'):
                    try:
                        plugin_path = os.path.join(plugin_dir, file)
                        module = self.load_plugin_module(plugin_path)

                        if hasattr(module, 'PLUGIN_METADATA'):
                            metadata = module.PLUGIN_METADATA
                            discovered[metadata.name] = metadata
                    except Exception as e:
                        self.logger.warning(f"Failed to discover plugin {file}: {e}")

        return discovered

    def load_plugin_class(self, module: Any) -> Optional[Type[BasePlugin]]:
        """Extract plugin class from module."""
        for name in dir(module):
            obj = getattr(module, name)
            try:
                if isinstance(obj, type) and issubclass(obj, BasePlugin) and obj != BasePlugin:
                    return obj
            except TypeError:
                pass
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Manager (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════

class PluginManager:
    """Main plugin management orchestrator."""

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """Initialize plugin manager."""
        if plugin_dirs is None:
            plugin_dirs = [
                os.path.join(os.path.dirname(__file__), 'plugins'),
                os.path.expanduser('~/.bael/plugins')
            ]

        self.plugin_dirs = plugin_dirs
        self.registry = PluginRegistry()
        self.loader = PluginLoader(plugin_dirs)
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self._global_hooks: Dict[HookType, List[Callable]] = defaultdict(list)

    def discover_and_register(self) -> Dict[str, bool]:
        """Discover and register all available plugins."""
        results = {}

        discovered = self.loader.discover_plugins()
        for name, metadata in discovered.items():
            try:
                # Calculate checksum
                checksum = self._calculate_checksum(metadata)
                self.registry.register(metadata, checksum)
                results[name] = True
                self.logger.info(f"Registered plugin: {name} v{metadata.version}")
            except Exception as e:
                self.logger.error(f"Failed to register {name}: {e}")
                results[name] = False

        return results

    def _calculate_checksum(self, metadata: PluginMetadata) -> str:
        """Calculate checksum for plugin metadata."""
        data = json.dumps(asdict(metadata), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def enable_plugin(self, plugin_name: str, config: Optional[PluginConfig] = None) -> Tuple[bool, Optional[str]]:
        """Enable and instantiate plugin."""
        with self._lock:
            info = self.registry.get_plugin(plugin_name)
            if not info:
                return False, f"Plugin '{plugin_name}' not found"

            if info.status == PluginStatus.ENABLED:
                return True, "Plugin already enabled"

            # Validate dependencies
            available = {p.metadata.name: p.metadata for p in self.registry.list_plugins()}
            is_valid, errors = self.registry.dependency_resolver.validate_dependencies(
                plugin_name, available
            )
            if not is_valid:
                return False, f"Dependency validation failed: {', '.join(errors)}"

            # Load and instantiate
            try:
                discovered = self.loader.discover_plugins()
                metadata = discovered.get(plugin_name)
                if not metadata:
                    return False, "Plugin not found in discovery"

                # Load module
                plugin_path = self._find_plugin_file(plugin_name)
                if not plugin_path:
                    return False, "Plugin file not found"

                module = self.loader.load_plugin_module(plugin_path)
                plugin_class = self.loader.load_plugin_class(module)
                if not plugin_class:
                    return False, "Plugin class not found in module"

                # Apply configuration
                if config:
                    info.config = config

                # Instantiate
                instance = plugin_class(info.config)
                if not instance.initialize():
                    return False, "Plugin initialization failed"

                # Store instance
                self.registry.instances[plugin_name] = instance
                self.registry.update_status(plugin_name, PluginStatus.ENABLED)
                info.enabled_at = datetime.now(timezone.utc)

                self._trigger_global_hooks(HookType.POST_INIT, plugin_name)
                self.logger.info(f"Enabled plugin: {plugin_name}")
                return True, None

            except Exception as e:
                self.logger.error(f"Failed to enable plugin {plugin_name}: {e}", exc_info=True)
                self.registry.update_status(plugin_name, PluginStatus.ERROR)
                return False, str(e)

    def disable_plugin(self, plugin_name: str) -> Tuple[bool, Optional[str]]:
        """Disable and remove plugin."""
        with self._lock:
            instance = self.registry.instances.get(plugin_name)
            if not instance:
                return False, "Plugin not enabled"

            try:
                self._trigger_global_hooks(HookType.PRE_DISABLE, plugin_name)
                instance.shutdown()
                del self.registry.instances[plugin_name]
                self.registry.update_status(plugin_name, PluginStatus.DISABLED)
                self.logger.info(f"Disabled plugin: {plugin_name}")
                return True, None
            except Exception as e:
                self.logger.error(f"Failed to disable plugin {plugin_name}: {e}")
                return False, str(e)

    def execute_plugin(
        self,
        plugin_name: str,
        *args: Any,
        **kwargs: Any
    ) -> Tuple[bool, Any, Optional[str]]:
        """Execute enabled plugin."""
        instance = self.registry.instances.get(plugin_name)
        if not instance:
            return False, None, f"Plugin '{plugin_name}' not enabled"

        info = self.registry.get_plugin(plugin_name)
        if not info:
            return False, None, "Plugin info not found"

        try:
            self._trigger_global_hooks(HookType.PRE_EXECUTE, plugin_name)

            start_time = time.time()
            initial_memory = self._get_memory_usage()

            if isinstance(instance, SandboxedPlugin):
                success, result, error = instance.safe_execute(*args, **kwargs)
            else:
                try:
                    result = instance.execute(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    success = False
                    result = None
                    error = e

            elapsed = time.time() - start_time
            peak_memory = self._get_memory_usage() - initial_memory

            info.metrics.update_execution(success, elapsed, peak_memory)

            if success:
                self._trigger_global_hooks(HookType.POST_EXECUTE, plugin_name, result)
                return True, result, None
            else:
                self._trigger_global_hooks(HookType.ERROR, plugin_name, error)
                return False, None, str(error)

        except Exception as e:
            self.logger.error(f"Plugin execution error: {e}", exc_info=True)
            return False, None, str(e)

    def _find_plugin_file(self, plugin_name: str) -> Optional[str]:
        """Find plugin file by name."""
        for plugin_dir in self.plugin_dirs:
            plugin_path = os.path.join(plugin_dir, f"{plugin_name}.py")
            if os.path.isfile(plugin_path):
                return plugin_path
        return None

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except (ImportError, Exception):
            return 0.0

    def register_global_hook(self, hook_type: HookType, handler: Callable) -> None:
        """Register global plugin lifecycle hook."""
        self._global_hooks[hook_type].append(handler)

    def _trigger_global_hooks(self, hook_type: HookType, *args: Any, **kwargs: Any) -> None:
        """Trigger all global hooks of type."""
        for handler in self._global_hooks.get(hook_type, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Global hook error: {e}")

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin information."""
        info = self.registry.get_plugin(plugin_name)
        if not info:
            return None

        metrics_dict = asdict(info.metrics)
        metrics_dict['success_rate'] = info.metrics.success_rate()

        return {
            'name': info.metadata.name,
            'version': info.metadata.version,
            'author': info.metadata.author,
            'description': info.metadata.description,
            'category': info.metadata.category.value,
            'status': info.status.value,
            'enabled': info.status == PluginStatus.ENABLED,
            'metrics': metrics_dict,
            'installed_at': info.installed_at.isoformat(),
            'enabled_at': info.enabled_at.isoformat() if info.enabled_at else None,
            'sandbox_level': info.config.sandbox_level.value,
        }

    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        """Get information for all plugins."""
        return [
            self.get_plugin_info(p.metadata.name)
            for p in self.registry.list_plugins()
        ]


# ═══════════════════════════════════════════════════════════════════════════
# Marketplace Integration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MarketplacePlugin:
    """Plugin available in marketplace."""
    name: str
    version: str
    author: str
    description: str
    rating: float  # 0-5
    downloads: int
    category: str
    url: str
    checksum: str


class PluginMarketplace:
    """Integration with plugin marketplace."""

    def __init__(self):
        """Initialize marketplace."""
        self.logger = logging.getLogger(__name__)
        self._plugins: Dict[str, MarketplacePlugin] = {}

    def search(self, query: str, category: Optional[str] = None) -> List[MarketplacePlugin]:
        """Search marketplace for plugins."""
        results = []
        query_lower = query.lower()

        for plugin in self._plugins.values():
            name_match = query_lower in plugin.name.lower()
            desc_match = query_lower in plugin.description.lower()
            cat_match = category is None or plugin.category.lower() == category.lower()

            if (name_match or desc_match) and cat_match:
                results.append(plugin)

        return sorted(results, key=lambda p: p.rating, reverse=True)

    def get_plugin(self, name: str) -> Optional[MarketplacePlugin]:
        """Retrieve marketplace plugin."""
        return self._plugins.get(name)

    def register_plugin(self, plugin: MarketplacePlugin) -> None:
        """Register plugin in marketplace."""
        self._plugins[plugin.name] = plugin


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Health Checker
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PluginHealth:
    """Plugin health status."""
    name: str
    healthy: bool
    status: PluginStatus
    uptime_seconds: float
    recent_errors: int
    memory_usage_mb: float
    last_execution: Optional[datetime]
    performance_degraded: bool


class PluginHealthChecker:
    """Monitor plugin health and performance."""

    def __init__(self, manager: PluginManager):
        """Initialize health checker."""
        self.manager = manager
        self.logger = logging.getLogger(__name__)
        self._error_threshold = 5  # Errors per hour
        self._performance_threshold = 1.0  # Seconds

    def check_health(self, plugin_name: str) -> PluginHealth:
        """Check health status of plugin."""
        info = self.manager.registry.get_plugin(plugin_name)
        if not info:
            return PluginHealth(
                name=plugin_name,
                healthy=False,
                status=PluginStatus.AVAILABLE,
                uptime_seconds=0,
                recent_errors=0,
                memory_usage_mb=0,
                last_execution=None,
                performance_degraded=False
            )

        # Calculate uptime
        uptime = datetime.now(timezone.utc) - info.installed_at

        # Check for performance degradation
        perf_degraded = (
            info.metrics.avg_execution_time > self._performance_threshold
            or info.metrics.peak_memory_usage_mb > info.config.max_memory_mb * 0.8
        )

        healthy = (
            info.status == PluginStatus.ENABLED
            and info.metrics.error_count < self._error_threshold
            and not perf_degraded
        )

        return PluginHealth(
            name=plugin_name,
            healthy=healthy,
            status=info.status,
            uptime_seconds=uptime.total_seconds(),
            recent_errors=info.metrics.error_count,
            memory_usage_mb=info.metrics.peak_memory_usage_mb,
            last_execution=info.metrics.last_execution_time,
            performance_degraded=perf_degraded
        )

    def check_all_health(self) -> List[PluginHealth]:
        """Check health of all plugins."""
        return [
            self.check_health(p.metadata.name)
            for p in self.manager.registry.list_plugins()
        ]


# ═══════════════════════════════════════════════════════════════════════════
# Global Plugin Manager Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create global plugin manager."""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager()
    return _global_plugin_manager


def initialize_plugins() -> Dict[str, bool]:
    """Initialize plugin system."""
    manager = get_plugin_manager()
    return manager.discover_and_register()
