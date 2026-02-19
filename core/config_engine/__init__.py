"""
BAEL Configuration Engine
=========================

Advanced configuration management with environments,
secrets, validation, and hot-reloading.

"Ba'el's settings transcend the mundane." — Ba'el
"""

from .config_manager import (
    # Enums
    ConfigFormat,
    ConfigSource,
    ValidationMode,
    SecretProvider,

    # Data structures
    ConfigValue,
    ConfigSchema,
    ConfigChange,
    ConfigManagerConfig,

    # Classes
    ConfigurationEngine,
    ConfigLoader,
    ConfigValidator,
    SecretManager,
    EnvironmentManager,

    # Instance
    config_engine
)

__all__ = [
    # Enums
    "ConfigFormat",
    "ConfigSource",
    "ValidationMode",
    "SecretProvider",

    # Data structures
    "ConfigValue",
    "ConfigSchema",
    "ConfigChange",
    "ConfigManagerConfig",

    # Classes
    "ConfigurationEngine",
    "ConfigLoader",
    "ConfigValidator",
    "SecretManager",
    "EnvironmentManager",

    # Instance
    "config_engine"
]
