"""
BAEL Plugin Engine
==================

Extensible plugin system for dynamic capability loading.

"Infinite expansion through modular power." — Ba'el
"""

from .plugin_manager import (
    # Enums
    PluginType,
    PluginStatus,
    PluginPriority,
    HookType,

    # Data structures
    Plugin,
    PluginMetadata,
    PluginConfig,
    Hook,
    PluginDependency,

    # Classes
    PluginEngine,
    PluginLoader,
    PluginRegistry,
    HookManager,
    PluginSandbox,

    # Instance
    plugin_engine
)

__all__ = [
    # Enums
    "PluginType",
    "PluginStatus",
    "PluginPriority",
    "HookType",

    # Data structures
    "Plugin",
    "PluginMetadata",
    "PluginConfig",
    "Hook",
    "PluginDependency",

    # Classes
    "PluginEngine",
    "PluginLoader",
    "PluginRegistry",
    "HookManager",
    "PluginSandbox",

    # Instance
    "plugin_engine"
]
