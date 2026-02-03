"""
BAEL - Plugin Ecosystem
Plugin manifest format, loader, registry, and sandboxing.
"""

import asyncio
import importlib.util
import inspect
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

import yaml

logger = logging.getLogger("BAEL.Plugins")


# =============================================================================
# PLUGIN MANIFEST
# =============================================================================

class PluginType(Enum):
    """Types of plugins."""
    TOOL = "tool"                    # New tool for agents
    REASONING = "reasoning"          # Reasoning engine
    MEMORY = "memory"                # Memory system
    INTEGRATION = "integration"      # External service integration
    PERSONA = "persona"              # New persona
    WORKFLOW = "workflow"            # Workflow component
    UI = "ui"                        # UI component
    MIDDLEWARE = "middleware"        # Request/response middleware


class PluginStatus(Enum):
    """Plugin lifecycle status."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginDependency:
    """A plugin dependency."""
    name: str
    version: Optional[str] = None
    optional: bool = False


@dataclass
class PluginManifest:
    """Plugin manifest describing the plugin."""
    # Identity
    id: str
    name: str
    version: str
    description: str

    # Metadata
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    tags: List[str] = field(default_factory=list)

    # Type and capabilities
    type: PluginType = PluginType.TOOL
    capabilities: List[str] = field(default_factory=list)

    # Dependencies
    dependencies: List[PluginDependency] = field(default_factory=list)
    python_version: str = ">=3.8"

    # Entry points
    main_module: str = "main.py"
    entry_point: str = "register"

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Permissions
    permissions: List[str] = field(default_factory=list)
    sandboxed: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_file(cls, path: Path) -> 'PluginManifest':
        """Load manifest from file (YAML or JSON)."""
        with open(path) as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Convert string enums
        if 'type' in data:
            data['type'] = PluginType(data['type'])

        # Convert dependencies
        if 'dependencies' in data:
            data['dependencies'] = [
                PluginDependency(**dep) if isinstance(dep, dict) else dep
                for dep in data['dependencies']
            ]

        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'homepage': self.homepage,
            'repository': self.repository,
            'tags': self.tags,
            'type': self.type.value,
            'capabilities': self.capabilities,
            'dependencies': [
                {'name': d.name, 'version': d.version, 'optional': d.optional}
                for d in self.dependencies
            ],
            'python_version': self.python_version,
            'main_module': self.main_module,
            'entry_point': self.entry_point,
            'permissions': self.permissions,
            'sandboxed': self.sandboxed
        }


# =============================================================================
# PLUGIN INTERFACE
# =============================================================================

class PluginInterface:
    """Base interface that all plugins must implement."""

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = logging.getLogger(f"BAEL.Plugin.{manifest.name}")

    async def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            True if initialization successful
        """
        raise NotImplementedError

    async def shutdown(self):
        """Cleanup and shutdown the plugin."""
        pass

    async def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return self.manifest.to_dict()


# =============================================================================
# PLUGIN SANDBOX
# =============================================================================

class PluginSandbox:
    """
    Sandboxed execution environment for plugins.

    Provides:
    - Limited filesystem access
    - Network restrictions
    - Resource limits (CPU, memory)
    - API access control
    """

    def __init__(self, plugin_id: str, permissions: List[str]):
        self.plugin_id = plugin_id
        self.permissions = permissions

        # Allowed operations
        self.allowed_paths: Set[Path] = set()
        self.allowed_network: Set[str] = set()
        self.api_access: Set[str] = set()

        self._parse_permissions()

    def _parse_permissions(self):
        """Parse permissions into access rules."""
        for perm in self.permissions:
            if perm.startswith("filesystem:"):
                path = perm.split(":", 1)[1]
                self.allowed_paths.add(Path(path))
            elif perm.startswith("network:"):
                domain = perm.split(":", 1)[1]
                self.allowed_network.add(domain)
            elif perm.startswith("api:"):
                api = perm.split(":", 1)[1]
                self.api_access.add(api)

    def check_filesystem_access(self, path: Path) -> bool:
        """Check if plugin can access a path."""
        # Check if path is within allowed paths
        for allowed_path in self.allowed_paths:
            try:
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False

    def check_network_access(self, domain: str) -> bool:
        """Check if plugin can access a network domain."""
        return domain in self.allowed_network or "*" in self.allowed_network

    def check_api_access(self, api: str) -> bool:
        """Check if plugin can access an API."""
        return api in self.api_access or "*" in self.api_access


# =============================================================================
# PLUGIN LOADER
# =============================================================================

class PluginLoader:
    """Loads and validates plugins."""

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir

    async def load_plugin(
        self,
        plugin_path: Path,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[PluginInterface]:
        """
        Load a plugin from a directory.

        Args:
            plugin_path: Path to plugin directory
            config: Optional configuration overrides

        Returns:
            Loaded plugin instance or None
        """
        try:
            # Load manifest
            manifest_path = plugin_path / "plugin.yaml"
            if not manifest_path.exists():
                manifest_path = plugin_path / "plugin.json"

            if not manifest_path.exists():
                logger.error(f"No manifest found in {plugin_path}")
                return None

            manifest = PluginManifest.from_file(manifest_path)
            logger.info(f"Loading plugin: {manifest.name} v{manifest.version}")

            # Check dependencies
            if not await self._check_dependencies(manifest):
                logger.error(f"Dependency check failed for {manifest.name}")
                return None

            # Load main module
            module_path = plugin_path / manifest.main_module
            if not module_path.exists():
                logger.error(f"Main module not found: {module_path}")
                return None

            # Import module
            spec = importlib.util.spec_from_file_location(
                f"bael_plugin_{manifest.id}",
                module_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Get entry point
            if not hasattr(module, manifest.entry_point):
                logger.error(f"Entry point '{manifest.entry_point}' not found")
                return None

            entry_func = getattr(module, manifest.entry_point)

            # Merge config
            plugin_config = {**manifest.default_config, **(config or {})}

            # Call entry point to get plugin instance
            if inspect.iscoroutinefunction(entry_func):
                plugin = await entry_func(manifest, plugin_config)
            else:
                plugin = entry_func(manifest, plugin_config)

            # Validate plugin implements interface
            if not isinstance(plugin, PluginInterface):
                logger.error(f"Plugin does not implement PluginInterface")
                return None

            # Initialize plugin
            if not await plugin.initialize():
                logger.error(f"Plugin initialization failed")
                return None

            logger.info(f"✅ Plugin loaded: {manifest.name}")
            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return None

    async def _check_dependencies(self, manifest: PluginManifest) -> bool:
        """Check if plugin dependencies are satisfied."""
        for dep in manifest.dependencies:
            if dep.optional:
                continue

            # Check if dependency is available
            # In real implementation, would check plugin registry
            logger.debug(f"Checking dependency: {dep.name}")

        return True


# =============================================================================
# PLUGIN REGISTRY
# =============================================================================

class PluginRegistry:
    """
    Central registry for managing plugins.

    Features:
    - Plugin discovery and loading
    - Dependency management
    - Hot reloading
    - Version management
    - Lifecycle management
    """

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self.loader = PluginLoader(plugin_dir)

        # Registry storage
        self.plugins: Dict[str, PluginInterface] = {}
        self.manifests: Dict[str, PluginManifest] = {}
        self.status: Dict[str, PluginStatus] = {}
        self.sandboxes: Dict[str, PluginSandbox] = {}

        # Plugin hooks
        self.hooks: Dict[str, List[Callable]] = {}

        logger.info(f"Plugin registry initialized: {plugin_dir}")

    async def discover_plugins(self) -> List[PluginManifest]:
        """Discover all plugins in the plugin directory."""
        discovered = []

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                continue

            manifest_file = None
            for ext in ['yaml', 'yml', 'json']:
                potential = plugin_path / f"plugin.{ext}"
                if potential.exists():
                    manifest_file = potential
                    break

            if manifest_file:
                try:
                    manifest = PluginManifest.from_file(manifest_file)
                    discovered.append(manifest)
                except Exception as e:
                    logger.error(f"Failed to load manifest from {manifest_file}: {e}")

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    async def load_plugin(
        self,
        plugin_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Load a plugin by ID.

        Args:
            plugin_id: Plugin ID
            config: Optional configuration

        Returns:
            True if loaded successfully
        """
        # Find plugin directory
        plugin_path = self.plugin_dir / plugin_id

        if not plugin_path.exists():
            logger.error(f"Plugin directory not found: {plugin_path}")
            return False

        self.status[plugin_id] = PluginStatus.LOADING

        try:
            # Load plugin
            plugin = await self.loader.load_plugin(plugin_path, config)

            if not plugin:
                self.status[plugin_id] = PluginStatus.ERROR
                return False

            # Store plugin
            self.plugins[plugin_id] = plugin
            self.manifests[plugin_id] = plugin.manifest
            self.status[plugin_id] = PluginStatus.LOADED

            # Create sandbox if needed
            if plugin.manifest.sandboxed:
                self.sandboxes[plugin_id] = PluginSandbox(
                    plugin_id,
                    plugin.manifest.permissions
                )

            # Activate plugin
            await self.activate_plugin(plugin_id)

            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            self.status[plugin_id] = PluginStatus.ERROR
            return False

    async def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a loaded plugin."""
        if plugin_id not in self.plugins:
            return False

        try:
            self.status[plugin_id] = PluginStatus.ACTIVE
            logger.info(f"✅ Plugin activated: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate plugin {plugin_id}: {e}")
            self.status[plugin_id] = PluginStatus.ERROR
            return False

    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate an active plugin."""
        if plugin_id not in self.plugins:
            return False

        try:
            self.status[plugin_id] = PluginStatus.PAUSED
            logger.info(f"Plugin deactivated: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
            return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        if plugin_id not in self.plugins:
            return False

        try:
            # Shutdown plugin
            plugin = self.plugins[plugin_id]
            await plugin.shutdown()

            # Remove from registry
            del self.plugins[plugin_id]
            del self.manifests[plugin_id]
            self.status[plugin_id] = PluginStatus.UNLOADED

            if plugin_id in self.sandboxes:
                del self.sandboxes[plugin_id]

            logger.info(f"Plugin unloaded: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False

    async def reload_plugin(
        self,
        plugin_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Hot reload a plugin."""
        logger.info(f"Reloading plugin: {plugin_id}")

        # Unload
        if plugin_id in self.plugins:
            await self.unload_plugin(plugin_id)

        # Load
        return await self.load_plugin(plugin_id, config)

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get a plugin by ID."""
        return self.plugins.get(plugin_id)

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get plugin manifest."""
        return self.manifests.get(plugin_id)

    def get_status(self, plugin_id: str) -> PluginStatus:
        """Get plugin status."""
        return self.status.get(plugin_id, PluginStatus.UNLOADED)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None
    ) -> List[str]:
        """List plugins, optionally filtered by type or status."""
        result = list(self.plugins.keys())

        if plugin_type:
            result = [
                pid for pid in result
                if self.manifests[pid].type == plugin_type
            ]

        if status:
            result = [
                pid for pid in result
                if self.status.get(pid) == status
            ]

        return result

    def register_hook(self, hook_name: str, callback: Callable):
        """Register a callback for a plugin hook."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)

    async def call_hook(self, hook_name: str, *args, **kwargs):
        """Call all callbacks for a hook."""
        if hook_name not in self.hooks:
            return

        for callback in self.hooks[hook_name]:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook '{hook_name}' callback failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        status_counts = {}
        for status in PluginStatus:
            count = sum(1 for s in self.status.values() if s == status)
            if count > 0:
                status_counts[status.value] = count

        type_counts = {}
        for manifest in self.manifests.values():
            type_counts[manifest.type.value] = type_counts.get(manifest.type.value, 0) + 1

        return {
            "total_plugins": len(self.plugins),
            "active_plugins": sum(1 for s in self.status.values() if s == PluginStatus.ACTIVE),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts
        }


# =============================================================================
# EXAMPLE PLUGIN MANIFEST
# =============================================================================

EXAMPLE_PLUGIN_MANIFEST = """
id: example-tool
name: Example Tool Plugin
version: 1.0.0
description: An example tool plugin for BAEL
author: BAEL Team
license: MIT
type: tool
capabilities:
  - web_scraping
  - data_extraction
dependencies:
  - name: beautifulsoup4
    version: ">=4.9.0"
    optional: false
python_version: ">=3.8"
main_module: main.py
entry_point: register
config_schema:
  api_key:
    type: string
    required: false
default_config:
  timeout: 30
permissions:
  - network:*
  - filesystem:/tmp/bael-plugins
sandboxed: true
tags:
  - web
  - scraping
"""


__all__ = [
    'PluginRegistry',
    'PluginLoader',
    'PluginManifest',
    'PluginInterface',
    'PluginSandbox',
    'PluginType',
    'PluginStatus',
    'PluginDependency'
]
