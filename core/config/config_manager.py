"""
BAEL - Configuration Management
Advanced configuration system with validation and hot-reload.

Features:
- YAML/JSON/ENV configuration
- Schema validation
- Environment overrides
- Hot reload
- Secrets management
- Configuration profiles
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ConfigFormat(Enum):
    """Configuration file formats."""
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    ENV = "env"
    INI = "ini"


class ValidationLevel(Enum):
    """Validation strictness levels."""
    NONE = "none"
    WARN = "warn"
    STRICT = "strict"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConfigValue:
    """A configuration value with metadata."""
    key: str
    value: Any
    source: str  # file, env, default, override
    type: Type
    required: bool = False
    secret: bool = False
    description: str = ""
    default: Any = None


@dataclass
class ConfigSchema:
    """Schema for configuration validation."""
    fields: Dict[str, "SchemaField"] = field(default_factory=dict)

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema."""
        errors = []

        for field_name, field_schema in self.fields.items():
            if field_name in config:
                value = config[field_name]
                field_errors = field_schema.validate(value)
                errors.extend([f"{field_name}: {e}" for e in field_errors])
            elif field_schema.required:
                errors.append(f"{field_name}: Required field missing")

        return errors


@dataclass
class SchemaField:
    """Schema for a single field."""
    type: Type
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    choices: Optional[List[Any]] = None
    nested: Optional["ConfigSchema"] = None

    def validate(self, value: Any) -> List[str]:
        """Validate a value against this field schema."""
        errors = []

        # Type check
        if not isinstance(value, self.type):
            errors.append(f"Expected {self.type.__name__}, got {type(value).__name__}")
            return errors

        # Range checks
        if self.min_value is not None and value < self.min_value:
            errors.append(f"Value {value} is less than minimum {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            errors.append(f"Value {value} is greater than maximum {self.max_value}")

        # Pattern check
        if self.pattern and isinstance(value, str):
            if not re.match(self.pattern, value):
                errors.append(f"Value does not match pattern {self.pattern}")

        # Choices check
        if self.choices and value not in self.choices:
            errors.append(f"Value must be one of {self.choices}")

        # Nested validation
        if self.nested and isinstance(value, dict):
            errors.extend(self.nested.validate(value))

        return errors


# =============================================================================
# CONFIG LOADERS
# =============================================================================

class ConfigLoader(ABC):
    """Abstract config loader."""

    @abstractmethod
    def load(self, source: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def save(self, config: Dict[str, Any], destination: str) -> None:
        pass


class YAMLLoader(ConfigLoader):
    """YAML configuration loader."""

    def load(self, source: str) -> Dict[str, Any]:
        try:
            import yaml

            with open(source, 'r') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML not installed, falling back to JSON-like YAML")
            return self._parse_simple_yaml(source)
        except Exception as e:
            logger.error(f"Failed to load YAML: {e}")
            return {}

    def _parse_simple_yaml(self, source: str) -> Dict[str, Any]:
        """Simple YAML parser for basic configs."""
        config = {}
        with open(source, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
        return config

    def save(self, config: Dict[str, Any], destination: str) -> None:
        try:
            import yaml

            with open(destination, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        except ImportError:
            # Fallback to JSON
            with open(destination, 'w') as f:
                json.dump(config, f, indent=2)


class JSONLoader(ConfigLoader):
    """JSON configuration loader."""

    def load(self, source: str) -> Dict[str, Any]:
        try:
            with open(source, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON: {e}")
            return {}

    def save(self, config: Dict[str, Any], destination: str) -> None:
        with open(destination, 'w') as f:
            json.dump(config, f, indent=2)


class EnvLoader(ConfigLoader):
    """Environment variable loader."""

    def __init__(self, prefix: str = "BAEL_"):
        self.prefix = prefix

    def load(self, source: str = "") -> Dict[str, Any]:
        config = {}

        # Load from .env file if provided
        if source and os.path.exists(source):
            self._load_env_file(source, config)

        # Override with actual environment variables
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                clean_key = key[len(self.prefix):].lower()
                config[clean_key] = self._parse_value(value)

        return config

    def _load_env_file(self, path: str, config: Dict[str, Any]) -> None:
        """Load .env file."""
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    if key.startswith(self.prefix):
                        clean_key = key[len(self.prefix):].lower()
                        config[clean_key] = self._parse_value(value)

    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def save(self, config: Dict[str, Any], destination: str) -> None:
        with open(destination, 'w') as f:
            for key, value in config.items():
                f.write(f"{self.prefix}{key.upper()}={value}\n")


# =============================================================================
# SECRETS MANAGER
# =============================================================================

class SecretsManager:
    """Manages sensitive configuration values."""

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._loaded_from: Set[str] = set()

    def load_from_env(self, keys: List[str]) -> None:
        """Load secrets from environment variables."""
        for key in keys:
            value = os.environ.get(key)
            if value:
                self._secrets[key] = value
                self._loaded_from.add("env")

    def load_from_file(self, path: str) -> None:
        """Load secrets from file."""
        if not os.path.exists(path):
            return

        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    self._secrets[key.strip()] = value.strip()

        self._loaded_from.add(path)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value."""
        return self._secrets.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Set a secret value."""
        self._secrets[key] = value

    def mask_value(self, value: str) -> str:
        """Mask a secret value for display."""
        if len(value) <= 8:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]


# =============================================================================
# CONFIGURATION
# =============================================================================

class Configuration:
    """Main configuration class."""

    def __init__(
        self,
        schema: Optional[ConfigSchema] = None,
        validation_level: ValidationLevel = ValidationLevel.WARN
    ):
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._overrides: Dict[str, Any] = {}
        self._schema = schema
        self._validation_level = validation_level
        self._loaders: Dict[ConfigFormat, ConfigLoader] = {
            ConfigFormat.YAML: YAMLLoader(),
            ConfigFormat.JSON: JSONLoader(),
            ConfigFormat.ENV: EnvLoader()
        }
        self._secrets = SecretsManager()
        self._watchers: List[Callable] = []
        self._loaded_files: Set[str] = set()

    def set_defaults(self, defaults: Dict[str, Any]) -> None:
        """Set default configuration values."""
        self._defaults = defaults
        self._merge_config()

    def load(
        self,
        source: str,
        format: Optional[ConfigFormat] = None
    ) -> bool:
        """Load configuration from file."""
        if format is None:
            format = self._detect_format(source)

        loader = self._loaders.get(format)
        if not loader:
            logger.error(f"No loader for format: {format}")
            return False

        try:
            loaded = loader.load(source)
            self._config.update(loaded)
            self._loaded_files.add(source)
            self._merge_config()

            # Validate
            if self._schema:
                errors = self._schema.validate(self._config)
                if errors:
                    if self._validation_level == ValidationLevel.STRICT:
                        raise ValueError(f"Configuration errors: {errors}")
                    else:
                        for error in errors:
                            logger.warning(f"Config validation: {error}")

            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False

    def load_env(self, prefix: str = "BAEL_") -> None:
        """Load configuration from environment variables."""
        loader = EnvLoader(prefix)
        env_config = loader.load()
        self._config.update(env_config)
        self._merge_config()

    def _detect_format(self, path: str) -> ConfigFormat:
        """Detect format from file extension."""
        ext = Path(path).suffix.lower()

        format_map = {
            '.yaml': ConfigFormat.YAML,
            '.yml': ConfigFormat.YAML,
            '.json': ConfigFormat.JSON,
            '.toml': ConfigFormat.TOML,
            '.env': ConfigFormat.ENV,
            '.ini': ConfigFormat.INI
        }

        return format_map.get(ext, ConfigFormat.YAML)

    def _merge_config(self) -> None:
        """Merge defaults, config, and overrides."""
        merged = {}
        merged.update(self._defaults)
        merged.update(self._config)
        merged.update(self._overrides)
        self._config = merged

    def get(
        self,
        key: str,
        default: Any = None,
        type_cast: Optional[Type] = None
    ) -> Any:
        """Get a configuration value."""
        # Support dot notation
        value = self._get_nested(key)

        if value is None:
            value = default

        if type_cast and value is not None:
            try:
                value = type_cast(value)
            except (ValueError, TypeError):
                pass

        return value

    def _get_nested(self, key: str) -> Any:
        """Get nested value using dot notation."""
        parts = key.split('.')
        value = self._config

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._set_nested(key, value)
        self._notify_watchers(key, value)

    def _set_nested(self, key: str, value: Any) -> None:
        """Set nested value using dot notation."""
        parts = key.split('.')
        config = self._config

        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        config[parts[-1]] = value

    def override(self, key: str, value: Any) -> None:
        """Override a configuration value."""
        self._overrides[key] = value
        self._merge_config()
        self._notify_watchers(key, value)

    def remove_override(self, key: str) -> None:
        """Remove an override."""
        if key in self._overrides:
            del self._overrides[key]
            self._merge_config()

    def watch(self, callback: Callable[[str, Any], None]) -> None:
        """Watch for configuration changes."""
        self._watchers.append(callback)

    def _notify_watchers(self, key: str, value: Any) -> None:
        """Notify watchers of changes."""
        for watcher in self._watchers:
            try:
                watcher(key, value)
            except Exception as e:
                logger.error(f"Watcher error: {e}")

    def save(self, destination: str, format: Optional[ConfigFormat] = None) -> bool:
        """Save configuration to file."""
        if format is None:
            format = self._detect_format(destination)

        loader = self._loaders.get(format)
        if not loader:
            return False

        try:
            loader.save(self._config, destination)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self._get_nested(key) is not None


# =============================================================================
# CONFIG PROFILES
# =============================================================================

class ConfigProfile:
    """Configuration profile for different environments."""

    def __init__(self, name: str, base: Optional[Configuration] = None):
        self.name = name
        self.config = Configuration()

        if base:
            self.config._config = base.to_dict().copy()

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply profile-specific overrides."""
        for key, value in overrides.items():
            self.config.set(key, value)


class ProfileManager:
    """Manages configuration profiles."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._profiles: Dict[str, ConfigProfile] = {}
        self._active_profile: Optional[str] = None

    def load_profile(self, name: str) -> Optional[ConfigProfile]:
        """Load a profile."""
        profile_path = os.path.join(self.config_dir, f"{name}.yaml")

        if not os.path.exists(profile_path):
            profile_path = os.path.join(self.config_dir, f"{name}.json")

        if not os.path.exists(profile_path):
            return None

        profile = ConfigProfile(name)
        profile.config.load(profile_path)

        self._profiles[name] = profile
        return profile

    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """Get a loaded profile."""
        return self._profiles.get(name)

    def set_active(self, name: str) -> bool:
        """Set the active profile."""
        if name not in self._profiles:
            self.load_profile(name)

        if name in self._profiles:
            self._active_profile = name
            return True
        return False

    @property
    def active(self) -> Optional[Configuration]:
        """Get active profile configuration."""
        if self._active_profile:
            profile = self._profiles.get(self._active_profile)
            return profile.config if profile else None
        return None


# =============================================================================
# HOT RELOAD
# =============================================================================

class ConfigWatcher:
    """Watch configuration files for changes."""

    def __init__(self, config: Configuration, interval: float = 5.0):
        self.config = config
        self.interval = interval
        self._running = False
        self._file_hashes: Dict[str, str] = {}
        self._task: Optional[asyncio.Task] = None

    def _hash_file(self, path: str) -> str:
        """Get hash of file contents."""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    async def start(self) -> None:
        """Start watching for changes."""
        self._running = True

        # Initial hashes
        for path in self.config._loaded_files:
            self._file_hashes[path] = self._hash_file(path)

        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _watch_loop(self) -> None:
        """Watch loop."""
        while self._running:
            await asyncio.sleep(self.interval)

            for path in self.config._loaded_files:
                new_hash = self._hash_file(path)
                old_hash = self._file_hashes.get(path)

                if new_hash and new_hash != old_hash:
                    logger.info(f"Config file changed: {path}")
                    self.config.load(path)
                    self._file_hashes[path] = new_hash


# =============================================================================
# BAEL DEFAULT CONFIG
# =============================================================================

def create_bael_config() -> Configuration:
    """Create BAEL default configuration."""
    config = Configuration()

    # Set defaults
    config.set_defaults({
        "app": {
            "name": "BAEL",
            "version": "1.0.0",
            "debug": False,
            "log_level": "INFO"
        },
        "llm": {
            "default_provider": "openai",
            "default_model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120
        },
        "memory": {
            "vector_db": "chromadb",
            "embedding_model": "text-embedding-3-small",
            "max_context_tokens": 100000
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8000,
            "cors_origins": ["*"]
        },
        "security": {
            "rate_limit": 100,
            "api_key_required": False
        },
        "cache": {
            "enabled": True,
            "ttl": 3600,
            "max_size": 1000
        }
    })

    # Load environment overrides
    config.load_env("BAEL_")

    return config


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_config():
    """Demonstrate configuration management."""
    config = create_bael_config()

    # Access values
    print(f"App name: {config.get('app.name')}")
    print(f"Debug mode: {config.get('app.debug')}")
    print(f"LLM provider: {config.get('llm.default_provider')}")

    # Set values
    config.set("app.debug", True)
    print(f"Debug mode after set: {config.get('app.debug')}")

    # Override
    config.override("llm.temperature", 0.5)
    print(f"Temperature: {config.get('llm.temperature')}")

    # Watch for changes
    def on_change(key: str, value: Any):
        print(f"Config changed: {key} = {value}")

    config.watch(on_change)
    config.set("app.log_level", "DEBUG")

    # Secrets
    config._secrets.set("OPENAI_API_KEY", "sk-test-xxx")
    key = config._secrets.get("OPENAI_API_KEY")
    print(f"API key (masked): {config._secrets.mask_value(key)}")

    # Profile management
    manager = ProfileManager("config")
    # Would load profiles from config/development.yaml, config/production.yaml, etc.

    print("\nConfiguration dictionary:")
    print(json.dumps(config.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(example_config())
