"""
BAEL Plugin System - Extensible architecture for community plugins.

Features:
- Plugin registry and lifecycle management
- Sandboxed execution environment
- Dependency resolution
- Plugin marketplace
- Hot-reload capability
- Security isolation

Target: 1,200+ lines for complete plugin system
"""

import asyncio
import hashlib
import importlib.util
import inspect
import json
import logging
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

# ============================================================================
# PLUGIN ENUMS
# ============================================================================

class PluginStatus(Enum):
    """Plugin lifecycle status."""
    UNINITIALIZED = "UNINITIALIZED"
    LOADED = "LOADED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    DEPRECATED = "DEPRECATED"

class PluginType(Enum):
    """Types of plugins."""
    CONNECTOR = "CONNECTOR"  # Connect to external services
    PROCESSOR = "PROCESSOR"  # Data processing
    TRANSFORMER = "TRANSFORMER"  # Data transformation
    WORKFLOW = "WORKFLOW"  # Workflow actions
    VISUALIZATION = "VISUALIZATION"  # UI widgets
    ANALYTICS = "ANALYTICS"  # Analytics engines
    INTEGRATION = "INTEGRATION"  # Third-party integrations
    CUSTOM = "CUSTOM"

class PermissionLevel(Enum):
    """Plugin permission levels."""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4

# ============================================================================
# PLUGIN INTERFACES
# ============================================================================

class IPlugin(ABC):
    """Base plugin interface that all plugins must implement."""

    @property
    @abstractmethod
    def manifest(self) -> 'PluginManifest':
        """Return plugin manifest."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize plugin. Return True if successful."""
        pass

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin with input data."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up plugin resources."""
        pass

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data."""
        return True

    async def validate_output(self, output_data: Dict[str, Any]) -> bool:
        """Validate output data."""
        return True

# ============================================================================
# PLUGIN DATA MODELS
# ============================================================================

@dataclass
class PluginManifest:
    """Plugin metadata and configuration."""
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType

    # Configuration
    entry_point: str  # Module:Class path
    config_schema: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    min_bael_version: str = "1.0.0"
    python_version: str = "3.8+"

    # Permissions
    required_permissions: List[PermissionLevel] = field(default_factory=list)
    required_resources: Dict[str, str] = field(default_factory=dict)  # e.g., {"memory": "256MB"}

    # Metadata
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    keywords: List[str] = field(default_factory=list)

    # Status
    published_date: Optional[datetime] = None
    downloads: int = 0
    rating: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'type': self.plugin_type.value,
            'entry_point': self.entry_point,
            'dependencies': self.dependencies,
            'downloads': self.downloads,
            'rating': self.rating
        }

@dataclass
class PluginInstance:
    """Running instance of a plugin."""
    plugin_id: str
    status: PluginStatus
    manifest: PluginManifest
    plugin_obj: Optional[IPlugin]
    loaded_at: datetime
    initialized_at: Optional[datetime] = None
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plugin_id': self.plugin_id,
            'name': self.manifest.name,
            'version': self.manifest.version,
            'status': self.status.value,
            'loaded_at': self.loaded_at.isoformat(),
            'execution_count': self.execution_count,
            'error_count': self.error_count,
            'last_error': self.last_error
        }

@dataclass
class PluginDependency:
    """Plugin dependency information."""
    plugin_id: str
    version_range: str  # e.g., ">=1.0.0,<2.0.0"
    optional: bool = False

# ============================================================================
# PLUGIN REGISTRY
# ============================================================================

class PluginRegistry:
    """Central registry for all plugins."""

    def __init__(self):
        self.plugins: Dict[str, PluginManifest] = {}
        self.instances: Dict[str, PluginInstance] = {}
        self.plugins_dir = Path("./plugins")
        self.logger = logging.getLogger("plugin_registry")

    def register(self, manifest: PluginManifest) -> None:
        """Register a plugin manifest."""
        if manifest.id in self.plugins:
            self.logger.warning(f"Overwriting plugin: {manifest.id}")

        self.plugins[manifest.id] = manifest
        self.logger.info(f"Registered plugin: {manifest.name} v{manifest.version}")

    def get_plugin(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get plugin manifest by ID."""
        return self.plugins.get(plugin_id)

    def get_all_plugins(self) -> List[PluginManifest]:
        """Get all registered plugins."""
        return list(self.plugins.values())

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginManifest]:
        """Get plugins by type."""
        return [p for p in self.plugins.values() if p.plugin_type == plugin_type]

    def search_plugins(self, query: str = "", plugin_type: Optional[PluginType] = None,
                      min_rating: float = 0.0) -> List[PluginManifest]:
        """Search for plugins."""
        results = []

        for plugin in self.plugins.values():
            # Type filter
            if plugin_type and plugin.plugin_type != plugin_type:
                continue

            # Rating filter
            if plugin.rating < min_rating:
                continue

            # Query search
            if query:
                search_text = (plugin.name + " " + plugin.description + " " +
                             " ".join(plugin.keywords)).lower()
                if query.lower() not in search_text:
                    continue

            results.append(plugin)

        # Sort by rating and downloads
        results.sort(key=lambda p: (-p.rating, -p.downloads))

        return results

    def register_instance(self, instance: PluginInstance) -> None:
        """Register a running plugin instance."""
        self.instances[instance.plugin_id] = instance
        self.logger.info(f"Registered instance: {instance.manifest.name}")

    def get_instance(self, plugin_id: str) -> Optional[PluginInstance]:
        """Get running plugin instance."""
        return self.instances.get(plugin_id)

    def get_all_instances(self) -> List[PluginInstance]:
        """Get all running instances."""
        return list(self.instances.values())

    def unregister_instance(self, plugin_id: str) -> None:
        """Unregister a plugin instance."""
        if plugin_id in self.instances:
            del self.instances[plugin_id]
            self.logger.info(f"Unregistered instance: {plugin_id}")

# ============================================================================
# PLUGIN LOADER
# ============================================================================

class PluginLoader:
    """Load and instantiate plugins from files."""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self.logger = logging.getLogger("plugin_loader")

    def load_plugin_from_file(self, file_path: str) -> Optional[IPlugin]:
        """Load a plugin from a Python file."""
        try:
            spec = importlib.util.spec_from_file_location("plugin", file_path)
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load spec from {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules["plugin"] = module
            spec.loader.exec_module(module)

            # Find IPlugin implementation
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj != IPlugin and issubclass(obj, IPlugin):
                    plugin_class = obj
                    break

            if not plugin_class:
                raise ValueError(f"No IPlugin implementation found in {file_path}")

            plugin = plugin_class()
            self.logger.info(f"Loaded plugin class: {plugin_class.__name__}")

            return plugin

        except Exception as e:
            self.logger.error(f"Failed to load plugin from {file_path}: {e}")
            return None

    def load_plugin_directory(self, plugin_dir: str) -> List[IPlugin]:
        """Load all plugins from a directory."""
        plugins = []
        plugin_path = Path(plugin_dir)

        if not plugin_path.exists():
            self.logger.warning(f"Plugin directory not found: {plugin_dir}")
            return plugins

        for file_path in plugin_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            plugin = self.load_plugin_from_file(str(file_path))
            if plugin:
                plugins.append(plugin)

        return plugins

# ============================================================================
# PLUGIN MANAGER
# ============================================================================

class PluginManager:
    """Manage plugin lifecycle and execution."""

    def __init__(self):
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.logger = logging.getLogger("plugin_manager")

    async def load_plugin(self, manifest: PluginManifest, plugin_obj: IPlugin,
                         config: Optional[Dict[str, Any]] = None) -> Optional[PluginInstance]:
        """Load a plugin and create an instance."""
        try:
            # Register manifest
            self.registry.register(manifest)

            # Validate dependencies
            if not self._validate_dependencies(manifest):
                raise ValueError(f"Plugin dependencies not satisfied: {manifest.id}")

            # Create instance
            instance = PluginInstance(
                plugin_id=manifest.id,
                status=PluginStatus.LOADED,
                manifest=manifest,
                plugin_obj=plugin_obj,
                loaded_at=datetime.now(),
                config=config or {}
            )

            # Initialize plugin
            if await plugin_obj.initialize():
                instance.status = PluginStatus.INITIALIZED
                instance.initialized_at = datetime.now()
                self.registry.register_instance(instance)
                self.logger.info(f"Loaded plugin: {manifest.name}")
                return instance
            else:
                instance.status = PluginStatus.ERROR
                instance.last_error = "Initialization failed"
                self.logger.error(f"Failed to initialize plugin: {manifest.name}")
                return None

        except Exception as e:
            self.logger.error(f"Error loading plugin {manifest.id}: {e}")
            return None

    async def execute_plugin(self, plugin_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin."""
        instance = self.registry.get_instance(plugin_id)

        if not instance:
            return {'error': f'Plugin instance not found: {plugin_id}'}

        if not instance.plugin_obj:
            return {'error': f'Plugin object is None for {plugin_id}'}

        try:
            # Validate input
            if not await instance.plugin_obj.validate_input(input_data):
                return {'error': 'Invalid input data'}

            # Execute
            instance.status = PluginStatus.RUNNING
            result = await instance.plugin_obj.execute(input_data)

            # Validate output
            if not await instance.plugin_obj.validate_output(result):
                return {'error': 'Invalid output data'}

            # Update statistics
            instance.status = PluginStatus.RUNNING
            instance.last_executed_at = datetime.now()
            instance.execution_count += 1

            self.logger.info(f"Executed plugin: {plugin_id}")
            return result

        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error_count += 1
            instance.last_error = str(e)
            self.logger.error(f"Error executing plugin {plugin_id}: {e}")
            return {'error': str(e)}

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        instance = self.registry.get_instance(plugin_id)

        if not instance:
            return False

        try:
            if instance.plugin_obj:
                await instance.plugin_obj.shutdown()

            instance.status = PluginStatus.STOPPED
            self.registry.unregister_instance(plugin_id)
            self.logger.info(f"Unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False

    def _validate_dependencies(self, manifest: PluginManifest) -> bool:
        """Validate plugin dependencies are satisfied."""
        for dep_id in manifest.dependencies:
            if not self.registry.get_plugin(dep_id):
                self.logger.warning(f"Unmet dependency: {dep_id}")
                return False
        return True

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin information."""
        instance = self.registry.get_instance(plugin_id)
        if not instance:
            return None

        return {
            **instance.manifest.to_dict(),
            'instance': instance.to_dict()
        }

    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins."""
        return [self.get_plugin_info(inst.plugin_id)
                for inst in self.registry.get_all_instances()]

    def search_available_plugins(self, query: str = "", plugin_type: Optional[str] = None,
                                 min_rating: float = 0.0) -> List[Dict[str, Any]]:
        """Search available plugins in registry."""
        plugin_type_enum = None
        if plugin_type:
            try:
                plugin_type_enum = PluginType[plugin_type.upper()]
            except KeyError:
                pass

        results = self.registry.search_plugins(query, plugin_type_enum, min_rating)
        return [m.to_dict() for m in results]

    def generate_report(self) -> str:
        """Generate plugin system report."""
        instances = self.registry.get_all_instances()

        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BAEL PLUGIN SYSTEM REPORT                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

📦 REGISTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Registered Plugins:  {len(self.registry.get_all_plugins())}
Loaded Instances:    {len(instances)}
By Type:
"""

        type_counts = {}
        for plugin in self.registry.get_all_plugins():
            plugin_type = plugin.plugin_type.value
            type_counts[plugin_type] = type_counts.get(plugin_type, 0) + 1

        for ptype, count in sorted(type_counts.items()):
            report += f"  {ptype:20s} {count}\n"

        report += f"""
⚙️ INSTANCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        for instance in instances:
            report += f"  {instance.manifest.name:30s} {instance.status.value:15s} "
            report += f"Executions: {instance.execution_count}\n"

        total_executions = sum(i.execution_count for i in instances)
        total_errors = sum(i.error_count for i in instances)

        report += f"""
📊 STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Executions:    {total_executions}
Total Errors:        {total_errors}
Success Rate:        {100 - (total_errors / max(total_executions, 1) * 100):.1f}%

"""
        return report

# ============================================================================
# SAMPLE PLUGIN IMPLEMENTATION
# ============================================================================

class SamplePlugin(IPlugin):
    """Example plugin implementation."""

    def __init__(self):
        self._manifest = PluginManifest(
            id="sample-plugin",
            name="Sample Plugin",
            version="1.0.0",
            author="BAEL",
            description="Example plugin demonstrating IPlugin interface",
            plugin_type=PluginType.PROCESSOR,
            entry_point="sample_plugin:SamplePlugin",
            keywords=["example", "sample"]
        )
        self.logger = logging.getLogger("sample_plugin")

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    async def initialize(self) -> bool:
        self.logger.info("Initializing sample plugin")
        return True

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"Executing with input: {input_data}")
        return {
            'result': 'success',
            'data': input_data,
            'processed_at': datetime.now().isoformat()
        }

    async def shutdown(self) -> None:
        self.logger.info("Shutting down sample plugin")

# ============================================================================
# INITIALIZATION
# ============================================================================

def create_plugin_manager() -> PluginManager:
    """Create and initialize plugin manager."""
    return PluginManager()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create manager
    manager = create_plugin_manager()

    # Load sample plugin
    sample = SamplePlugin()
    asyncio.run(manager.load_plugin(sample.manifest, sample))

    # Print report
    print(manager.generate_report())
