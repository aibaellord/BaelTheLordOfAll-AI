#!/usr/bin/env python3
"""
BAEL - Configuration Manager
Comprehensive configuration management with multiple sources,
validation, hot-reloading, and environment support.

Features:
- Multiple configuration sources (files, env, memory)
- Configuration validation
- Hot reloading
- Environment overlays
- Secrets management
- Type coercion
- Default values
- Change notifications
- Configuration profiles
- Dot notation access
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import reduce
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConfigSource(Enum):
    """Configuration source types."""
    FILE = "file"
    ENVIRONMENT = "environment"
    MEMORY = "memory"
    REMOTE = "remote"
    DEFAULT = "default"


class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    INI = "ini"
    ENV = "env"
    TOML = "toml"


class ValidationLevel(Enum):
    """Validation strictness levels."""
    NONE = "none"
    WARN = "warn"
    STRICT = "strict"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource = ConfigSource.DEFAULT
    timestamp: float = field(default_factory=time.time)
    is_secret: bool = False
    is_readonly: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigSchema:
    """Schema for configuration validation."""
    key: str
    type: Type = str
    required: bool = False
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""
    secret: bool = False
    choices: List[Any] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None


@dataclass
class ConfigChange:
    """Configuration change event."""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key: str = ""
    old_value: Any = None
    new_value: Any = None
    source: ConfigSource = ConfigSource.MEMORY
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConfigProfile:
    """Configuration profile."""
    name: str
    description: str = ""
    values: Dict[str, Any] = field(default_factory=dict)
    parent: Optional[str] = None
    active: bool = False


# =============================================================================
# CONFIGURATION SOURCES
# =============================================================================

class ConfigSourceProvider(ABC):
    """Abstract configuration source provider."""

    @property
    @abstractmethod
    def source_type(self) -> ConfigSource:
        """Get source type."""
        pass

    @abstractmethod
    async def load(self) -> Dict[str, Any]:
        """Load configuration from source."""
        pass

    async def save(self, config: Dict[str, Any]) -> bool:
        """Save configuration to source (optional)."""
        return False

    async def watch(
        self,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Watch for configuration changes (optional)."""
        pass


class MemoryConfigSource(ConfigSourceProvider):
    """In-memory configuration source."""

    def __init__(self, initial: Dict[str, Any] = None):
        self._data = initial or {}

    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.MEMORY

    async def load(self) -> Dict[str, Any]:
        return self._data.copy()

    async def save(self, config: Dict[str, Any]) -> bool:
        self._data = config.copy()
        return True


class EnvironmentConfigSource(ConfigSourceProvider):
    """Environment variables configuration source."""

    def __init__(
        self,
        prefix: str = "",
        separator: str = "__"
    ):
        self.prefix = prefix
        self.separator = separator

    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.ENVIRONMENT

    async def load(self) -> Dict[str, Any]:
        result = {}

        for key, value in os.environ.items():
            if self.prefix and not key.startswith(self.prefix):
                continue

            # Remove prefix
            config_key = key
            if self.prefix:
                config_key = key[len(self.prefix):]
                if config_key.startswith("_"):
                    config_key = config_key[1:]

            # Convert separator to dots
            config_key = config_key.replace(self.separator, ".")
            config_key = config_key.lower()

            # Try to parse value
            parsed = self._parse_value(value)

            # Set nested value
            self._set_nested(result, config_key, parsed)

        return result

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # None
        if value.lower() in ("null", "none", ""):
            return None

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        return value

    def _set_nested(
        self,
        data: Dict,
        key: str,
        value: Any
    ) -> None:
        """Set nested value using dot notation."""
        parts = key.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


class FileConfigSource(ConfigSourceProvider):
    """File-based configuration source."""

    def __init__(
        self,
        path: str,
        format: ConfigFormat = None,
        watch_changes: bool = False
    ):
        self.path = Path(path)
        self.format = format or self._detect_format()
        self.watch_changes = watch_changes
        self._last_modified: Optional[float] = None

    def _detect_format(self) -> ConfigFormat:
        """Detect format from file extension."""
        suffix = self.path.suffix.lower()

        formats = {
            ".json": ConfigFormat.JSON,
            ".yaml": ConfigFormat.YAML,
            ".yml": ConfigFormat.YAML,
            ".ini": ConfigFormat.INI,
            ".env": ConfigFormat.ENV,
            ".toml": ConfigFormat.TOML
        }

        return formats.get(suffix, ConfigFormat.JSON)

    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.FILE

    async def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}

        content = self.path.read_text(encoding="utf-8")
        self._last_modified = self.path.stat().st_mtime

        if self.format == ConfigFormat.JSON:
            return json.loads(content)

        if self.format == ConfigFormat.ENV:
            return self._parse_env(content)

        # For YAML/TOML/INI, return as-is (would need external libraries)
        return json.loads(content)

    async def save(self, config: Dict[str, Any]) -> bool:
        try:
            if self.format == ConfigFormat.JSON:
                content = json.dumps(config, indent=2)
            else:
                content = json.dumps(config, indent=2)

            self.path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def _parse_env(self, content: str) -> Dict[str, Any]:
        """Parse .env format."""
        result = {}

        for line in content.split("\n"):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value

        return result

    async def watch(
        self,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Watch file for changes."""
        if not self.watch_changes:
            return

        while True:
            await asyncio.sleep(1.0)

            if self.path.exists():
                mtime = self.path.stat().st_mtime

                if self._last_modified and mtime > self._last_modified:
                    try:
                        config = await self.load()
                        await callback(config)
                    except Exception as e:
                        logger.error(f"Failed to reload config: {e}")


# =============================================================================
# CONFIGURATION VALIDATOR
# =============================================================================

class ConfigValidator:
    """Configuration validator."""

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.WARN
    ):
        self.level = level
        self.schemas: Dict[str, ConfigSchema] = {}

    def add_schema(self, schema: ConfigSchema) -> None:
        """Add a schema for a key."""
        self.schemas[schema.key] = schema

    def validate(
        self,
        config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate configuration against schemas."""
        errors = []

        for key, schema in self.schemas.items():
            value = self._get_nested(config, key)

            # Required check
            if schema.required and value is None:
                errors.append(f"Missing required config: {key}")
                continue

            if value is None:
                continue

            # Type check
            if not isinstance(value, schema.type):
                try:
                    # Try coercion
                    value = schema.type(value)
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid type for {key}: expected {schema.type.__name__}"
                    )
                    continue

            # Choices check
            if schema.choices and value not in schema.choices:
                errors.append(
                    f"Invalid value for {key}: must be one of {schema.choices}"
                )

            # Range check
            if schema.min_value is not None and value < schema.min_value:
                errors.append(f"Value for {key} below minimum: {schema.min_value}")

            if schema.max_value is not None and value > schema.max_value:
                errors.append(f"Value for {key} above maximum: {schema.max_value}")

            # Pattern check
            if schema.pattern and isinstance(value, str):
                if not re.match(schema.pattern, value):
                    errors.append(f"Value for {key} doesn't match pattern")

            # Custom validator
            if schema.validator and not schema.validator(value):
                errors.append(f"Custom validation failed for {key}")

        if errors and self.level == ValidationLevel.STRICT:
            return False, errors

        if errors and self.level == ValidationLevel.WARN:
            for error in errors:
                logger.warning(f"Config validation: {error}")

        return len(errors) == 0, errors

    def _get_nested(self, data: Dict, key: str) -> Any:
        """Get nested value using dot notation."""
        try:
            return reduce(
                lambda d, k: d[k],
                key.split("."),
                data
            )
        except (KeyError, TypeError):
            return None


# =============================================================================
# SECRETS MANAGER
# =============================================================================

class SecretsManager:
    """Simple secrets manager."""

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._masked_value = "********"

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret value."""
        self._secrets[key] = value

    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        return self._secrets.get(key)

    def mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask secret values in config."""
        result = config.copy()

        for key in self._secrets:
            if key in result:
                result[key] = self._masked_value

        return result

    def load_from_env(self, prefix: str = "SECRET_") -> None:
        """Load secrets from environment."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                secret_key = key[len(prefix):].lower()
                self._secrets[secret_key] = value


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigurationManager:
    """
    Comprehensive Configuration Manager for BAEL.
    """

    def __init__(
        self,
        validation_level: ValidationLevel = ValidationLevel.WARN
    ):
        self._config: Dict[str, ConfigValue] = {}
        self._sources: List[ConfigSourceProvider] = []
        self._validator = ConfigValidator(validation_level)
        self._secrets = SecretsManager()
        self._profiles: Dict[str, ConfigProfile] = {}
        self._active_profile: Optional[str] = None

        # Change listeners
        self._change_listeners: List[Callable[[ConfigChange], Awaitable[None]]] = []

        # Cache
        self._cache: Dict[str, Any] = {}
        self._cache_dirty = True

    def add_source(self, source: ConfigSourceProvider) -> None:
        """Add a configuration source."""
        self._sources.append(source)

    def add_schema(self, schema: ConfigSchema) -> None:
        """Add a validation schema."""
        self._validator.add_schema(schema)

    def add_profile(self, profile: ConfigProfile) -> None:
        """Add a configuration profile."""
        self._profiles[profile.name] = profile

    def activate_profile(self, name: str) -> bool:
        """Activate a profile."""
        if name not in self._profiles:
            return False

        # Deactivate current
        if self._active_profile:
            self._profiles[self._active_profile].active = False

        self._profiles[name].active = True
        self._active_profile = name
        self._cache_dirty = True

        return True

    async def load(self) -> bool:
        """Load configuration from all sources."""
        merged = {}

        # Load from each source in order
        for source in self._sources:
            try:
                data = await source.load()
                merged = self._deep_merge(merged, data)
            except Exception as e:
                logger.error(f"Failed to load from {source.source_type}: {e}")

        # Apply active profile
        if self._active_profile and self._active_profile in self._profiles:
            profile = self._profiles[self._active_profile]
            merged = self._deep_merge(merged, profile.values)

        # Validate
        valid, errors = self._validator.validate(merged)

        if not valid and self._validator.level == ValidationLevel.STRICT:
            raise ValueError(f"Configuration validation failed: {errors}")

        # Store values
        for key, value in self._flatten(merged).items():
            self._config[key] = ConfigValue(
                key=key,
                value=value,
                source=ConfigSource.FILE  # Simplified
            )

        self._cache = merged
        self._cache_dirty = False

        return True

    async def save(self) -> bool:
        """Save configuration to writable sources."""
        config = self._build_config()

        for source in self._sources:
            try:
                await source.save(config)
            except Exception as e:
                logger.error(f"Failed to save to {source.source_type}: {e}")
                return False

        return True

    def get(
        self,
        key: str,
        default: T = None,
        type_hint: Type[T] = None
    ) -> T:
        """Get configuration value."""
        value = self._get_nested(self._cache, key)

        if value is None:
            return default

        if type_hint:
            try:
                return type_hint(value)
            except (ValueError, TypeError):
                return default

        return value

    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.MEMORY
    ) -> None:
        """Set configuration value."""
        old_value = self.get(key)

        # Update cache
        self._set_nested(self._cache, key, value)

        # Update config
        self._config[key] = ConfigValue(
            key=key,
            value=value,
            source=source
        )

        self._cache_dirty = True

        # Notify listeners
        change = ConfigChange(
            key=key,
            old_value=old_value,
            new_value=value,
            source=source
        )

        asyncio.create_task(self._notify_change(change))

    def has(self, key: str) -> bool:
        """Check if key exists."""
        return self._get_nested(self._cache, key) is not None

    def delete(self, key: str) -> bool:
        """Delete a configuration key."""
        if key in self._config:
            old_value = self.get(key)
            del self._config[key]

            # Remove from cache
            parts = key.split(".")
            current = self._cache

            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    return False

            if parts[-1] in current:
                del current[parts[-1]]

            self._cache_dirty = True

            change = ConfigChange(
                key=key,
                old_value=old_value,
                new_value=None
            )
            asyncio.create_task(self._notify_change(change))

            return True

        return False

    def get_all(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Get all configuration."""
        config = self._cache.copy()

        if mask_secrets:
            config = self._secrets.mask_secrets(config)

        return config

    def on_change(
        self,
        listener: Callable[[ConfigChange], Awaitable[None]]
    ) -> None:
        """Register change listener."""
        self._change_listeners.append(listener)

    async def _notify_change(self, change: ConfigChange) -> None:
        """Notify change listeners."""
        for listener in self._change_listeners:
            try:
                await listener(change)
            except Exception as e:
                logger.error(f"Change listener error: {e}")

    def _deep_merge(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _flatten(
        self,
        data: Dict[str, Any],
        prefix: str = ""
    ) -> Dict[str, Any]:
        """Flatten nested dictionary."""
        result = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self._flatten(value, full_key))
            else:
                result[full_key] = value

        return result

    def _get_nested(self, data: Dict, key: str) -> Any:
        """Get nested value using dot notation."""
        try:
            return reduce(
                lambda d, k: d[k],
                key.split("."),
                data
            )
        except (KeyError, TypeError):
            return None

    def _set_nested(
        self,
        data: Dict,
        key: str,
        value: Any
    ) -> None:
        """Set nested value using dot notation."""
        parts = key.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _build_config(self) -> Dict[str, Any]:
        """Build configuration dictionary."""
        return self._cache.copy()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Configuration Manager."""
    print("=" * 70)
    print("BAEL - CONFIGURATION MANAGER DEMO")
    print("Comprehensive Configuration Management")
    print("=" * 70)
    print()

    manager = ConfigurationManager()

    # 1. Add Memory Source
    print("1. ADD CONFIGURATION SOURCES:")
    print("-" * 40)

    memory_source = MemoryConfigSource({
        "app": {
            "name": "BAEL",
            "version": "1.0.0",
            "debug": True
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "bael_db"
        },
        "api": {
            "rate_limit": 100,
            "timeout": 30
        }
    })

    manager.add_source(memory_source)
    print("   Added: MemoryConfigSource")

    env_source = EnvironmentConfigSource(prefix="BAEL_")
    manager.add_source(env_source)
    print("   Added: EnvironmentConfigSource (prefix: BAEL_)")
    print()

    # 2. Add Schemas
    print("2. ADD VALIDATION SCHEMAS:")
    print("-" * 40)

    schemas = [
        ConfigSchema(
            key="app.name",
            type=str,
            required=True,
            description="Application name"
        ),
        ConfigSchema(
            key="database.port",
            type=int,
            required=True,
            min_value=1,
            max_value=65535
        ),
        ConfigSchema(
            key="api.rate_limit",
            type=int,
            default=50,
            min_value=1,
            max_value=1000
        )
    ]

    for schema in schemas:
        manager.add_schema(schema)
        print(f"   Schema: {schema.key} ({schema.type.__name__})")
    print()

    # 3. Load Configuration
    print("3. LOAD CONFIGURATION:")
    print("-" * 40)

    await manager.load()
    print("   Configuration loaded successfully")
    print()

    # 4. Get Values
    print("4. GET CONFIGURATION VALUES:")
    print("-" * 40)

    print(f"   app.name: {manager.get('app.name')}")
    print(f"   app.version: {manager.get('app.version')}")
    print(f"   app.debug: {manager.get('app.debug')}")
    print(f"   database.host: {manager.get('database.host')}")
    print(f"   database.port: {manager.get('database.port', type_hint=int)}")
    print(f"   api.rate_limit: {manager.get('api.rate_limit')}")
    print(f"   nonexistent: {manager.get('nonexistent', default='N/A')}")
    print()

    # 5. Set Values
    print("5. SET CONFIGURATION VALUES:")
    print("-" * 40)

    manager.set("app.debug", False)
    print(f"   Set app.debug = False")

    manager.set("new.setting", "value123")
    print(f"   Set new.setting = 'value123'")

    print(f"   Verify app.debug: {manager.get('app.debug')}")
    print(f"   Verify new.setting: {manager.get('new.setting')}")
    print()

    # 6. Configuration Profiles
    print("6. CONFIGURATION PROFILES:")
    print("-" * 40)

    dev_profile = ConfigProfile(
        name="development",
        description="Development environment",
        values={
            "app": {"debug": True},
            "database": {"host": "localhost"}
        }
    )

    prod_profile = ConfigProfile(
        name="production",
        description="Production environment",
        values={
            "app": {"debug": False},
            "database": {"host": "db.production.com"}
        }
    )

    manager.add_profile(dev_profile)
    manager.add_profile(prod_profile)

    print("   Added profiles: development, production")

    manager.activate_profile("development")
    await manager.load()
    print(f"   Active profile: development")
    print(f"   database.host: {manager.get('database.host')}")

    manager.activate_profile("production")
    await manager.load()
    print(f"   Active profile: production")
    print(f"   database.host: {manager.get('database.host')}")
    print()

    # 7. Change Listeners
    print("7. CHANGE LISTENERS:")
    print("-" * 40)

    changes = []

    async def on_change(change: ConfigChange):
        changes.append(change)
        print(f"   Change: {change.key} = {change.new_value}")

    manager.on_change(on_change)

    manager.set("listener.test1", "value1")
    manager.set("listener.test2", "value2")

    await asyncio.sleep(0.1)
    print(f"   Total changes recorded: {len(changes)}")
    print()

    # 8. Has and Delete
    print("8. HAS AND DELETE:")
    print("-" * 40)

    print(f"   Has 'app.name': {manager.has('app.name')}")
    print(f"   Has 'nonexistent': {manager.has('nonexistent')}")

    manager.set("temp.key", "temp_value")
    print(f"   Created temp.key: {manager.has('temp.key')}")

    manager.delete("temp.key")
    print(f"   After delete: {manager.has('temp.key')}")
    print()

    # 9. Get All Configuration
    print("9. GET ALL CONFIGURATION:")
    print("-" * 40)

    all_config = manager.get_all()
    print(f"   Total sections: {len(all_config)}")
    for section in all_config:
        print(f"   - {section}")
    print()

    # 10. Secrets Manager
    print("10. SECRETS MANAGER:")
    print("-" * 40)

    manager._secrets.set_secret("api_key", "super_secret_key_123")
    manager._secrets.set_secret("password", "my_password")

    manager.set("api_key", "super_secret_key_123")
    manager.set("password", "my_password")

    masked = manager.get_all(mask_secrets=True)
    print(f"   api_key (masked): {masked.get('api_key', 'not set')}")

    original = manager.get("api_key")
    print(f"   api_key (original): {original}")
    print()

    # 11. Environment Source
    print("11. ENVIRONMENT SOURCE:")
    print("-" * 40)

    # Simulate environment variables
    os.environ["BAEL_APP__DEBUG"] = "true"
    os.environ["BAEL_DATABASE__PORT"] = "3306"

    env_config = await env_source.load()
    print(f"   Environment config keys: {list(env_config.keys())}")
    print()

    # 12. File Source (simulated)
    print("12. FILE SOURCE:")
    print("-" * 40)

    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "file": {"setting": "from_file"}
        }, f)
        temp_path = f.name

    file_source = FileConfigSource(temp_path)
    file_config = await file_source.load()
    print(f"   Loaded from file: {file_config}")

    os.unlink(temp_path)
    print()

    # Clean up environment
    os.environ.pop("BAEL_APP__DEBUG", None)
    os.environ.pop("BAEL_DATABASE__PORT", None)

    print("=" * 70)
    print("DEMO COMPLETE - Configuration Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
