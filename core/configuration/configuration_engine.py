#!/usr/bin/env python3
"""
BAEL - Configuration Engine
Configuration management for agents.

Features:
- Configuration sources
- Environment-based config
- Config validation
- Dynamic reloading
- Secret management
"""

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConfigSource(Enum):
    """Configuration sources."""
    DEFAULT = "default"
    FILE = "file"
    ENV = "env"
    REMOTE = "remote"
    OVERRIDE = "override"


class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    ENV = "env"
    INI = "ini"


class ValidationResult(Enum):
    """Validation results."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class ConfigChangeType(Enum):
    """Configuration change types."""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ConfigValue:
    """A configuration value."""
    key: str = ""
    value: Any = None
    source: ConfigSource = ConfigSource.DEFAULT
    secret: bool = False
    description: str = ""
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    schema_id: str = ""
    key: str = ""
    value_type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""
    validator: Optional[Callable] = None

    def __post_init__(self):
        if not self.schema_id:
            self.schema_id = str(uuid.uuid4())[:8]


@dataclass
class ValidationError:
    """Validation error."""
    key: str = ""
    message: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class ConfigChange:
    """Configuration change."""
    change_id: str = ""
    key: str = ""
    change_type: ConfigChangeType = ConfigChangeType.MODIFIED
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.change_id:
            self.change_id = str(uuid.uuid4())[:8]


@dataclass
class ConfigProfile:
    """Configuration profile."""
    profile_id: str = ""
    name: str = ""
    values: Dict[str, Any] = field(default_factory=dict)
    active: bool = False

    def __post_init__(self):
        if not self.profile_id:
            self.profile_id = str(uuid.uuid4())[:8]


@dataclass
class ConfigEngineSettings:
    """Configuration engine settings."""
    env_prefix: str = ""
    auto_reload: bool = False
    reload_interval: float = 60.0
    validate_on_load: bool = True


# =============================================================================
# CONFIG LOADER
# =============================================================================

class ConfigLoader:
    """Load configuration from sources."""

    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON config file."""
        if not path.exists():
            return {}

        with open(path, "r") as f:
            return json.load(f)

    def load_env_file(self, path: Path) -> Dict[str, str]:
        """Load .env file."""
        values = {}

        if not path.exists():
            return values

        with open(path, "r") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()

                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    values[key] = value

        return values

    def load_env(self, prefix: str = "") -> Dict[str, str]:
        """Load from environment variables."""
        values = {}

        for key, value in os.environ.items():
            if prefix:
                if key.startswith(prefix):
                    clean_key = key[len(prefix):].lstrip("_")
                    values[clean_key] = value
            else:
                values[key] = value

        return values


# =============================================================================
# CONFIG STORE
# =============================================================================

class ConfigStore:
    """Store configuration values."""

    def __init__(self):
        self._values: Dict[str, ConfigValue] = {}
        self._layers: Dict[ConfigSource, Dict[str, Any]] = defaultdict(dict)

    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.DEFAULT,
        secret: bool = False
    ) -> ConfigValue:
        """Set a configuration value."""
        self._layers[source][key] = value

        resolved_value = self._resolve(key)
        resolved_source = self._get_source(key)

        config_value = ConfigValue(
            key=key,
            value=resolved_value,
            source=resolved_source,
            secret=secret
        )

        self._values[key] = config_value

        return config_value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        config_value = self._values.get(key)

        if config_value:
            return config_value.value

        return default

    def get_config(self, key: str) -> Optional[ConfigValue]:
        """Get configuration object."""
        return self._values.get(key)

    def _resolve(self, key: str) -> Any:
        """Resolve value from layers."""
        priority = [
            ConfigSource.OVERRIDE,
            ConfigSource.ENV,
            ConfigSource.REMOTE,
            ConfigSource.FILE,
            ConfigSource.DEFAULT
        ]

        for source in priority:
            if key in self._layers.get(source, {}):
                return self._layers[source][key]

        return None

    def _get_source(self, key: str) -> ConfigSource:
        """Get source for key."""
        priority = [
            ConfigSource.OVERRIDE,
            ConfigSource.ENV,
            ConfigSource.REMOTE,
            ConfigSource.FILE,
            ConfigSource.DEFAULT
        ]

        for source in priority:
            if key in self._layers.get(source, {}):
                return source

        return ConfigSource.DEFAULT

    def delete(self, key: str) -> bool:
        """Delete a configuration."""
        if key in self._values:
            del self._values[key]

            for layer in self._layers.values():
                if key in layer:
                    del layer[key]

            return True

        return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._values

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self._values.keys())

    def all(self) -> Dict[str, Any]:
        """Get all values."""
        return {k: v.value for k, v in self._values.items()}

    def count(self) -> int:
        """Count configurations."""
        return len(self._values)

    def clear(self) -> int:
        """Clear all configurations."""
        count = len(self._values)
        self._values.clear()
        self._layers.clear()
        return count


# =============================================================================
# VALIDATOR
# =============================================================================

class ConfigValidator:
    """Validate configuration."""

    def __init__(self):
        self._schemas: Dict[str, ConfigSchema] = {}

    def add_schema(self, schema: ConfigSchema) -> None:
        """Add validation schema."""
        self._schemas[schema.key] = schema

    def validate(self, key: str, value: Any) -> Tuple[ValidationResult, Optional[str]]:
        """Validate a single value."""
        schema = self._schemas.get(key)

        if not schema:
            return ValidationResult.VALID, None

        if value is None and schema.required:
            return ValidationResult.INVALID, f"Required field '{key}' is missing"

        if value is not None:
            expected_type = schema.value_type

            if expected_type == "string" and not isinstance(value, str):
                return ValidationResult.INVALID, f"Expected string for '{key}'"

            elif expected_type == "int" and not isinstance(value, int):
                return ValidationResult.INVALID, f"Expected int for '{key}'"

            elif expected_type == "float" and not isinstance(value, (int, float)):
                return ValidationResult.INVALID, f"Expected float for '{key}'"

            elif expected_type == "bool" and not isinstance(value, bool):
                return ValidationResult.INVALID, f"Expected bool for '{key}'"

            elif expected_type == "list" and not isinstance(value, list):
                return ValidationResult.INVALID, f"Expected list for '{key}'"

            elif expected_type == "dict" and not isinstance(value, dict):
                return ValidationResult.INVALID, f"Expected dict for '{key}'"

        if schema.validator and value is not None:
            try:
                if not schema.validator(value):
                    return ValidationResult.INVALID, f"Custom validation failed for '{key}'"
            except Exception as e:
                return ValidationResult.INVALID, f"Validation error for '{key}': {e}"

        return ValidationResult.VALID, None

    def validate_all(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate all configurations."""
        errors = []

        for key, schema in self._schemas.items():
            value = config.get(key)

            result, message = self.validate(key, value)

            if result == ValidationResult.INVALID:
                errors.append(ValidationError(
                    key=key,
                    message=message or "Validation failed",
                    expected=schema.value_type,
                    actual=type(value).__name__ if value else "None"
                ))

        return errors


# =============================================================================
# CHANGE TRACKER
# =============================================================================

class ChangeTracker:
    """Track configuration changes."""

    def __init__(self, max_history: int = 100):
        self._history: List[ConfigChange] = []
        self._max_history = max_history
        self._callbacks: List[Callable] = []

    def track(
        self,
        key: str,
        change_type: ConfigChangeType,
        old_value: Any = None,
        new_value: Any = None
    ) -> ConfigChange:
        """Track a change."""
        change = ConfigChange(
            key=key,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value
        )

        self._history.append(change)

        if len(self._history) > self._max_history:
            self._history.pop(0)

        for callback in self._callbacks:
            callback(change)

        return change

    def on_change(self, callback: Callable) -> None:
        """Add change callback."""
        self._callbacks.append(callback)

    def get_history(self, key: Optional[str] = None) -> List[ConfigChange]:
        """Get change history."""
        if key:
            return [c for c in self._history if c.key == key]
        return list(self._history)

    def clear_history(self) -> int:
        """Clear history."""
        count = len(self._history)
        self._history.clear()
        return count


# =============================================================================
# PROFILE MANAGER
# =============================================================================

class ProfileManager:
    """Manage configuration profiles."""

    def __init__(self):
        self._profiles: Dict[str, ConfigProfile] = {}
        self._active: Optional[str] = None

    def create(self, name: str, values: Dict[str, Any]) -> ConfigProfile:
        """Create a profile."""
        profile = ConfigProfile(
            name=name,
            values=values
        )

        self._profiles[profile.profile_id] = profile

        return profile

    def get(self, profile_id: str) -> Optional[ConfigProfile]:
        """Get profile by ID."""
        return self._profiles.get(profile_id)

    def get_by_name(self, name: str) -> Optional[ConfigProfile]:
        """Get profile by name."""
        for profile in self._profiles.values():
            if profile.name == name:
                return profile
        return None

    def activate(self, profile_id: str) -> bool:
        """Activate a profile."""
        profile = self._profiles.get(profile_id)

        if not profile:
            return False

        if self._active:
            old_profile = self._profiles.get(self._active)
            if old_profile:
                old_profile.active = False

        profile.active = True
        self._active = profile_id

        return True

    def get_active(self) -> Optional[ConfigProfile]:
        """Get active profile."""
        if self._active:
            return self._profiles.get(self._active)
        return None

    def list(self) -> List[ConfigProfile]:
        """List all profiles."""
        return list(self._profiles.values())

    def delete(self, profile_id: str) -> bool:
        """Delete a profile."""
        if profile_id in self._profiles:
            if self._active == profile_id:
                self._active = None
            del self._profiles[profile_id]
            return True
        return False


# =============================================================================
# CONFIGURATION ENGINE
# =============================================================================

class ConfigurationEngine:
    """
    Configuration Engine for BAEL.

    Configuration management and validation.
    """

    def __init__(self, settings: Optional[ConfigEngineSettings] = None):
        self._settings = settings or ConfigEngineSettings()

        self._store = ConfigStore()
        self._loader = ConfigLoader()
        self._validator = ConfigValidator()
        self._tracker = ChangeTracker()
        self._profiles = ProfileManager()

    # ----- Set/Get Operations -----

    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.DEFAULT,
        secret: bool = False
    ) -> ConfigValue:
        """Set a configuration value."""
        old_value = self._store.get(key)

        config_value = self._store.set(key, value, source, secret)

        if old_value is None:
            self._tracker.track(key, ConfigChangeType.ADDED, None, value)
        elif old_value != value:
            self._tracker.track(key, ConfigChangeType.MODIFIED, old_value, value)

        return config_value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._store.get(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """Get string value."""
        value = self.get(key)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer value."""
        value = self.get(key)
        if value is None:
            return default
        return int(value)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float value."""
        value = self.get(key)
        if value is None:
            return default
        return float(value)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean value."""
        value = self.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get list value."""
        value = self.get(key)
        if value is None:
            return default or []
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(",")]

    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """Get dict value."""
        value = self.get(key)
        if value is None:
            return default or {}
        if isinstance(value, dict):
            return value
        return json.loads(value)

    def delete(self, key: str) -> bool:
        """Delete a configuration."""
        old_value = self.get(key)
        result = self._store.delete(key)

        if result:
            self._tracker.track(key, ConfigChangeType.REMOVED, old_value, None)

        return result

    def exists(self, key: str) -> bool:
        """Check if configuration exists."""
        return self._store.exists(key)

    # ----- Load Operations -----

    def load_json(self, path: str) -> int:
        """Load from JSON file."""
        data = self._loader.load_json(Path(path))

        count = 0
        for key, value in data.items():
            self.set(key, value, ConfigSource.FILE)
            count += 1

        return count

    def load_env_file(self, path: str = ".env") -> int:
        """Load from .env file."""
        data = self._loader.load_env_file(Path(path))

        count = 0
        for key, value in data.items():
            self.set(key, value, ConfigSource.FILE)
            count += 1

        return count

    def load_env(self, prefix: Optional[str] = None) -> int:
        """Load from environment variables."""
        if prefix is None:
            prefix = self._settings.env_prefix

        data = self._loader.load_env(prefix)

        count = 0
        for key, value in data.items():
            self.set(key, value, ConfigSource.ENV)
            count += 1

        return count

    # ----- Validation -----

    def add_schema(
        self,
        key: str,
        value_type: str = "string",
        required: bool = False,
        default: Any = None,
        validator: Optional[Callable] = None
    ) -> ConfigSchema:
        """Add validation schema."""
        schema = ConfigSchema(
            key=key,
            value_type=value_type,
            required=required,
            default=default,
            validator=validator
        )

        self._validator.add_schema(schema)

        return schema

    def validate(self, key: str) -> Tuple[bool, Optional[str]]:
        """Validate a configuration."""
        value = self.get(key)
        result, message = self._validator.validate(key, value)
        return result == ValidationResult.VALID, message

    def validate_all(self) -> List[ValidationError]:
        """Validate all configurations."""
        return self._validator.validate_all(self._store.all())

    # ----- Change Tracking -----

    def on_change(self, callback: Callable) -> None:
        """Add change callback."""
        self._tracker.on_change(callback)

    def get_history(self, key: Optional[str] = None) -> List[ConfigChange]:
        """Get change history."""
        return self._tracker.get_history(key)

    # ----- Profiles -----

    def create_profile(self, name: str, values: Dict[str, Any]) -> ConfigProfile:
        """Create a configuration profile."""
        return self._profiles.create(name, values)

    def activate_profile(self, name: str) -> bool:
        """Activate a profile by name."""
        profile = self._profiles.get_by_name(name)

        if not profile:
            return False

        if self._profiles.activate(profile.profile_id):
            for key, value in profile.values.items():
                self.set(key, value, ConfigSource.OVERRIDE)
            return True

        return False

    def get_active_profile(self) -> Optional[ConfigProfile]:
        """Get active profile."""
        return self._profiles.get_active()

    def list_profiles(self) -> List[str]:
        """List profile names."""
        return [p.name for p in self._profiles.list()]

    # ----- Export/Import -----

    def export(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export all configurations."""
        result = {}

        for key in self._store.keys():
            config = self._store.get_config(key)
            if config:
                if config.secret and not include_secrets:
                    result[key] = "***"
                else:
                    result[key] = config.value

        return result

    def import_config(
        self,
        data: Dict[str, Any],
        source: ConfigSource = ConfigSource.FILE
    ) -> int:
        """Import configurations."""
        count = 0

        for key, value in data.items():
            self.set(key, value, source)
            count += 1

        return count

    # ----- Info -----

    def keys(self) -> List[str]:
        """Get all configuration keys."""
        return self._store.keys()

    def count(self) -> int:
        """Count configurations."""
        return self._store.count()

    def get_source(self, key: str) -> Optional[ConfigSource]:
        """Get source for a configuration."""
        config = self._store.get_config(key)
        if config:
            return config.source
        return None

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        configs = self._store.keys()

        by_source = defaultdict(int)
        secrets = 0

        for key in configs:
            config = self._store.get_config(key)
            if config:
                by_source[config.source.value] += 1
                if config.secret:
                    secrets += 1

        return {
            "total_configs": len(configs),
            "by_source": dict(by_source),
            "secrets": secrets,
            "profiles": len(self._profiles.list()),
            "active_profile": self._profiles.get_active().name if self._profiles.get_active() else None,
            "history_entries": len(self._tracker.get_history())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Configuration Engine."""
    print("=" * 70)
    print("BAEL - CONFIGURATION ENGINE DEMO")
    print("Configuration Management")
    print("=" * 70)
    print()

    engine = ConfigurationEngine()

    # 1. Set Configurations
    print("1. SET CONFIGURATIONS:")
    print("-" * 40)

    engine.set("app.name", "BAEL")
    engine.set("app.version", "1.0.0")
    engine.set("app.debug", True)
    engine.set("server.host", "0.0.0.0")
    engine.set("server.port", 8080)
    engine.set("database.url", "postgresql://localhost/bael")
    engine.set("api.key", "secret-api-key-123", secret=True)

    print(f"   Set 7 configurations")
    print(f"   Total configs: {engine.count()}")
    print()

    # 2. Get Configurations
    print("2. GET CONFIGURATIONS:")
    print("-" * 40)

    print(f"   app.name: {engine.get('app.name')}")
    print(f"   app.version: {engine.get('app.version')}")
    print(f"   app.debug: {engine.get('app.debug')}")
    print(f"   server.port: {engine.get('server.port')}")
    print()

    # 3. Typed Getters
    print("3. TYPED GETTERS:")
    print("-" * 40)

    engine.set("max_workers", "8")
    engine.set("rate_limit", "100.5")
    engine.set("enabled", "true")
    engine.set("allowed_hosts", "localhost,127.0.0.1")

    print(f"   get_str('app.name'): {engine.get_str('app.name')} ({type(engine.get_str('app.name')).__name__})")
    print(f"   get_int('max_workers'): {engine.get_int('max_workers')} ({type(engine.get_int('max_workers')).__name__})")
    print(f"   get_float('rate_limit'): {engine.get_float('rate_limit')} ({type(engine.get_float('rate_limit')).__name__})")
    print(f"   get_bool('enabled'): {engine.get_bool('enabled')} ({type(engine.get_bool('enabled')).__name__})")
    print(f"   get_list('allowed_hosts'): {engine.get_list('allowed_hosts')}")
    print()

    # 4. Default Values
    print("4. DEFAULT VALUES:")
    print("-" * 40)

    print(f"   get('missing'): {engine.get('missing')}")
    print(f"   get('missing', 'default'): {engine.get('missing', 'default')}")
    print(f"   get_int('missing', 42): {engine.get_int('missing', 42)}")
    print(f"   get_bool('missing', True): {engine.get_bool('missing', True)}")
    print()

    # 5. Configuration Sources
    print("5. CONFIGURATION SOURCES:")
    print("-" * 40)

    engine.set("from_default", "default_value", ConfigSource.DEFAULT)
    engine.set("from_file", "file_value", ConfigSource.FILE)
    engine.set("from_env", "env_value", ConfigSource.ENV)
    engine.set("from_override", "override_value", ConfigSource.OVERRIDE)

    for key in ["from_default", "from_file", "from_env", "from_override"]:
        source = engine.get_source(key)
        print(f"   {key}: {engine.get(key)} (source: {source.value})")
    print()

    # 6. Source Priority
    print("6. SOURCE PRIORITY:")
    print("-" * 40)

    engine.set("priority_test", "default", ConfigSource.DEFAULT)
    print(f"   After DEFAULT: {engine.get('priority_test')}")

    engine.set("priority_test", "from_file", ConfigSource.FILE)
    print(f"   After FILE: {engine.get('priority_test')}")

    engine.set("priority_test", "from_env", ConfigSource.ENV)
    print(f"   After ENV: {engine.get('priority_test')}")

    engine.set("priority_test", "override", ConfigSource.OVERRIDE)
    print(f"   After OVERRIDE: {engine.get('priority_test')}")
    print()

    # 7. Validation Schema
    print("7. VALIDATION SCHEMA:")
    print("-" * 40)

    engine.add_schema("server.port", "int", required=True)
    engine.add_schema("app.name", "string", required=True)
    engine.add_schema("app.debug", "bool", required=False)
    engine.add_schema(
        "email", "string", required=True,
        validator=lambda v: "@" in v
    )

    valid, msg = engine.validate("server.port")
    print(f"   server.port valid: {valid}")

    valid, msg = engine.validate("app.name")
    print(f"   app.name valid: {valid}")

    engine.set("email", "invalid-email")
    valid, msg = engine.validate("email")
    print(f"   email (invalid) valid: {valid} - {msg}")

    engine.set("email", "valid@email.com")
    valid, msg = engine.validate("email")
    print(f"   email (valid) valid: {valid}")
    print()

    # 8. Validate All
    print("8. VALIDATE ALL:")
    print("-" * 40)

    errors = engine.validate_all()
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   - {error.key}: {error.message}")
    print()

    # 9. Change Tracking
    print("9. CHANGE TRACKING:")
    print("-" * 40)

    changes = []
    engine.on_change(lambda c: changes.append(c))

    engine.set("tracked.value", "initial")
    engine.set("tracked.value", "modified")
    engine.delete("tracked.value")

    print(f"   Changes tracked: {len(changes)}")
    for change in changes:
        print(f"   - {change.key}: {change.change_type.value}")
    print()

    # 10. Change History
    print("10. CHANGE HISTORY:")
    print("-" * 40)

    history = engine.get_history()
    print(f"   Total history entries: {len(history)}")
    for entry in history[-3:]:
        print(f"   - {entry.key}: {entry.change_type.value} ({entry.old_value} -> {entry.new_value})")
    print()

    # 11. Configuration Profiles
    print("11. CONFIGURATION PROFILES:")
    print("-" * 40)

    dev_profile = engine.create_profile("development", {
        "app.debug": True,
        "log.level": "DEBUG",
        "database.url": "postgresql://localhost/bael_dev"
    })
    print(f"   Created: {dev_profile.name}")

    prod_profile = engine.create_profile("production", {
        "app.debug": False,
        "log.level": "INFO",
        "database.url": "postgresql://prod.db/bael"
    })
    print(f"   Created: {prod_profile.name}")

    print(f"   Profiles: {engine.list_profiles()}")
    print()

    # 12. Activate Profile
    print("12. ACTIVATE PROFILE:")
    print("-" * 40)

    print(f"   Before activation:")
    print(f"   - app.debug: {engine.get('app.debug')}")

    engine.activate_profile("development")

    print(f"   After activating 'development':")
    print(f"   - app.debug: {engine.get('app.debug')}")
    print(f"   - log.level: {engine.get('log.level')}")

    active = engine.get_active_profile()
    print(f"   Active profile: {active.name if active else 'None'}")
    print()

    # 13. Export Configurations
    print("13. EXPORT CONFIGURATIONS:")
    print("-" * 40)

    exported = engine.export(include_secrets=False)
    print(f"   Exported {len(exported)} configs")
    print(f"   api.key (no secrets): {exported.get('api.key')}")

    exported_with_secrets = engine.export(include_secrets=True)
    print(f"   api.key (with secrets): {exported_with_secrets.get('api.key')}")
    print()

    # 14. Import Configurations
    print("14. IMPORT CONFIGURATIONS:")
    print("-" * 40)

    new_config = {
        "imported.setting1": "value1",
        "imported.setting2": "value2",
        "imported.setting3": 42
    }

    count = engine.import_config(new_config)
    print(f"   Imported {count} configurations")
    print(f"   imported.setting1: {engine.get('imported.setting1')}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Configuration Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
