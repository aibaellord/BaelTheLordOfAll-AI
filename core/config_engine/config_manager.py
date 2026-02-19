"""
BAEL Configuration Engine
=========================

Comprehensive configuration management with:
- Multiple format support (JSON, YAML, TOML, ENV)
- Environment-based configuration
- Secret management
- Schema validation
- Hot-reloading
- Configuration inheritance
- Type coercion

"Ba'el's configuration shapes reality." — Ba'el
"""

import asyncio
import logging
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import uuid
from pathlib import Path
import copy

logger = logging.getLogger("BAEL.ConfigEngine")


# ============================================================================
# ENUMS
# ============================================================================

class ConfigFormat(Enum):
    """Supported configuration formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"
    INI = "ini"
    PYTHON = "python"


class ConfigSource(Enum):
    """Configuration sources."""
    FILE = "file"
    ENVIRONMENT = "environment"
    COMMAND_LINE = "command_line"
    DEFAULT = "default"
    REMOTE = "remote"
    DATABASE = "database"
    SECRET_STORE = "secret_store"


class ValidationMode(Enum):
    """Configuration validation modes."""
    NONE = "none"
    WARN = "warn"
    STRICT = "strict"


class SecretProvider(Enum):
    """Secret storage providers."""
    ENV = "env"
    FILE = "file"
    VAULT = "vault"
    AWS_SECRETS = "aws_secrets"
    AZURE_KEYVAULT = "azure_keyvault"
    GCP_SECRETS = "gcp_secrets"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ConfigValue:
    """A configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource = ConfigSource.DEFAULT
    secret: bool = False
    encrypted: bool = False
    expires_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the value has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def masked_value(self) -> Any:
        """Get a masked version of the value for logging."""
        if self.secret:
            if isinstance(self.value, str) and len(self.value) > 4:
                return f"{self.value[:2]}{'*' * (len(self.value) - 4)}{self.value[-2:]}"
            return "***"
        return self.value


@dataclass
class ConfigSchema:
    """Schema definition for a configuration key."""
    key: str
    type: Type
    required: bool = True
    default: Any = None
    description: str = ""
    secret: bool = False

    # Validation
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    choices: Optional[List[Any]] = None

    # Environment
    env_var: Optional[str] = None

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value against this schema."""
        # Type check
        if not isinstance(value, self.type):
            try:
                value = self.type(value)
            except (ValueError, TypeError):
                return False, f"Expected type {self.type.__name__}, got {type(value).__name__}"

        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False, f"Value {value} is less than minimum {self.min_value}"
        if self.max_value is not None and value > self.max_value:
            return False, f"Value {value} is greater than maximum {self.max_value}"

        # Length validation
        if hasattr(value, '__len__'):
            if self.min_length is not None and len(value) < self.min_length:
                return False, f"Length {len(value)} is less than minimum {self.min_length}"
            if self.max_length is not None and len(value) > self.max_length:
                return False, f"Length {len(value)} is greater than maximum {self.max_length}"

        # Pattern validation
        if self.pattern and isinstance(value, str):
            if not re.match(self.pattern, value):
                return False, f"Value does not match pattern {self.pattern}"

        # Choices validation
        if self.choices and value not in self.choices:
            return False, f"Value {value} not in allowed choices {self.choices}"

        return True, None


@dataclass
class ConfigChange:
    """Record of a configuration change."""
    key: str
    old_value: Any
    new_value: Any
    source: ConfigSource
    timestamp: datetime = field(default_factory=datetime.now)
    user: Optional[str] = None


@dataclass
class ConfigManagerConfig:
    """Configuration for the config manager itself."""
    validation_mode: ValidationMode = ValidationMode.WARN
    enable_hot_reload: bool = True
    reload_interval_seconds: float = 30.0
    enable_change_tracking: bool = True
    max_change_history: int = 1000
    enable_encryption: bool = False
    encryption_key: Optional[str] = None


# ============================================================================
# CONFIG LOADER
# ============================================================================

class ConfigLoader:
    """
    Load configuration from various sources and formats.
    """

    def __init__(self):
        """Initialize config loader."""
        self._loaders: Dict[ConfigFormat, Callable[[str], Dict]] = {
            ConfigFormat.JSON: self._load_json,
            ConfigFormat.ENV: self._load_env,
        }

        # Try to add YAML support
        try:
            import yaml
            self._loaders[ConfigFormat.YAML] = self._load_yaml
        except ImportError:
            pass

        # Try to add TOML support
        try:
            import tomllib  # Python 3.11+
            self._loaders[ConfigFormat.TOML] = self._load_toml
        except ImportError:
            try:
                import toml
                self._loaders[ConfigFormat.TOML] = self._load_toml_legacy
            except ImportError:
                pass

    def load_file(self, path: Union[str, Path], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a file."""
        path = Path(path)

        if format is None:
            format = self._detect_format(path)

        if format not in self._loaders:
            raise ValueError(f"Unsupported format: {format}")

        content = path.read_text()
        return self._loaders[format](content)

    def load_string(self, content: str, format: ConfigFormat) -> Dict[str, Any]:
        """Load configuration from a string."""
        if format not in self._loaders:
            raise ValueError(f"Unsupported format: {format}")
        return self._loaders[format](content)

    def load_environment(self, prefix: str = "") -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        prefix_upper = prefix.upper()

        for key, value in os.environ.items():
            if prefix_upper and not key.startswith(prefix_upper):
                continue

            config_key = key[len(prefix_upper):].lstrip("_").lower()
            config[config_key] = self._parse_env_value(value)

        return config

    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect format from file extension."""
        suffix = path.suffix.lower()
        format_map = {
            '.json': ConfigFormat.JSON,
            '.yaml': ConfigFormat.YAML,
            '.yml': ConfigFormat.YAML,
            '.toml': ConfigFormat.TOML,
            '.env': ConfigFormat.ENV,
            '.ini': ConfigFormat.INI,
        }
        return format_map.get(suffix, ConfigFormat.JSON)

    def _load_json(self, content: str) -> Dict[str, Any]:
        """Load JSON configuration."""
        return json.loads(content)

    def _load_yaml(self, content: str) -> Dict[str, Any]:
        """Load YAML configuration."""
        import yaml
        return yaml.safe_load(content) or {}

    def _load_toml(self, content: str) -> Dict[str, Any]:
        """Load TOML configuration (Python 3.11+)."""
        import tomllib
        return tomllib.loads(content)

    def _load_toml_legacy(self, content: str) -> Dict[str, Any]:
        """Load TOML configuration (legacy)."""
        import toml
        return toml.loads(content)

    def _load_env(self, content: str) -> Dict[str, Any]:
        """Load .env format configuration."""
        config = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                config[key.lower()] = self._parse_env_value(value)

        return config

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False

        # None
        if value.lower() in ('null', 'none', ''):
            return None

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # JSON (for complex values)
        if value.startswith(('[', '{')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value


# ============================================================================
# CONFIG VALIDATOR
# ============================================================================

class ConfigValidator:
    """
    Validate configuration against schemas.
    """

    def __init__(self, mode: ValidationMode = ValidationMode.WARN):
        """Initialize validator."""
        self.mode = mode
        self._schemas: Dict[str, ConfigSchema] = {}

    def register_schema(self, schema: ConfigSchema) -> None:
        """Register a configuration schema."""
        self._schemas[schema.key] = schema

    def register_schemas(self, schemas: List[ConfigSchema]) -> None:
        """Register multiple schemas."""
        for schema in schemas:
            self.register_schema(schema)

    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration against schemas."""
        errors = []

        # Check required keys
        for key, schema in self._schemas.items():
            if schema.required and key not in config:
                errors.append(f"Required key missing: {key}")

        # Validate present keys
        for key, value in config.items():
            if key in self._schemas:
                valid, error = self._schemas[key].validate(value)
                if not valid:
                    errors.append(f"{key}: {error}")

        if errors and self.mode == ValidationMode.STRICT:
            raise ValueError(f"Configuration validation failed: {errors}")
        elif errors and self.mode == ValidationMode.WARN:
            for error in errors:
                logger.warning(f"Config validation: {error}")

        return len(errors) == 0, errors

    def get_defaults(self) -> Dict[str, Any]:
        """Get default values for all schemas."""
        return {
            key: schema.default
            for key, schema in self._schemas.items()
            if schema.default is not None
        }


# ============================================================================
# SECRET MANAGER
# ============================================================================

class SecretManager:
    """
    Manage secrets and sensitive configuration.
    """

    def __init__(self, provider: SecretProvider = SecretProvider.ENV):
        """Initialize secret manager."""
        self.provider = provider
        self._cache: Dict[str, ConfigValue] = {}
        self._secret_keys: Set[str] = set()

    def mark_secret(self, key: str) -> None:
        """Mark a configuration key as a secret."""
        self._secret_keys.add(key)

    def is_secret(self, key: str) -> bool:
        """Check if a key is marked as secret."""
        return key in self._secret_keys

    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        # Check cache
        if key in self._cache:
            cached = self._cache[key]
            if not cached.is_expired():
                return cached.value

        # Get from provider
        value = await self._fetch_from_provider(key)

        if value is not None:
            self._cache[key] = ConfigValue(
                key=key,
                value=value,
                source=ConfigSource.SECRET_STORE,
                secret=True,
                expires_at=datetime.now() + timedelta(hours=1)
            )

        return value

    async def _fetch_from_provider(self, key: str) -> Optional[str]:
        """Fetch secret from provider."""
        if self.provider == SecretProvider.ENV:
            return os.environ.get(key.upper())

        elif self.provider == SecretProvider.FILE:
            # Docker secrets style
            secret_path = Path(f"/run/secrets/{key}")
            if secret_path.exists():
                return secret_path.read_text().strip()

        # Other providers would be implemented here
        # (Vault, AWS Secrets Manager, etc.)

        return None

    def mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask secret values in a configuration dict."""
        masked = {}
        for key, value in config.items():
            if self.is_secret(key):
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
                else:
                    masked[key] = "***"
            elif isinstance(value, dict):
                masked[key] = self.mask_secrets(value)
            else:
                masked[key] = value
        return masked


# ============================================================================
# ENVIRONMENT MANAGER
# ============================================================================

class EnvironmentManager:
    """
    Manage environment-specific configurations.
    """

    def __init__(self):
        """Initialize environment manager."""
        self._environments: Dict[str, Dict[str, Any]] = {}
        self._current_environment: str = "development"
        self._inheritance: Dict[str, str] = {}  # child -> parent

    def set_environment(self, name: str) -> None:
        """Set the current environment."""
        self._current_environment = name
        logger.info(f"Environment set to: {name}")

    def get_environment(self) -> str:
        """Get the current environment."""
        return self._current_environment

    def define_environment(
        self,
        name: str,
        config: Dict[str, Any],
        inherits_from: Optional[str] = None
    ) -> None:
        """Define an environment."""
        self._environments[name] = config
        if inherits_from:
            self._inheritance[name] = inherits_from

    def get_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for an environment."""
        env = environment or self._current_environment

        # Build inheritance chain
        chain = []
        current = env
        while current:
            if current in self._environments:
                chain.append(current)
            current = self._inheritance.get(current)

        # Merge from base to specific
        config = {}
        for env_name in reversed(chain):
            self._deep_merge(config, self._environments.get(env_name, {}))

        return config

    def _deep_merge(self, base: Dict, overlay: Dict) -> None:
        """Deep merge overlay into base."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    @staticmethod
    def detect_environment() -> str:
        """Detect environment from system."""
        # Check common environment variables
        for var in ['ENVIRONMENT', 'ENV', 'BAEL_ENV', 'APP_ENV', 'NODE_ENV']:
            if var in os.environ:
                return os.environ[var].lower()

        # Check for common indicators
        if os.path.exists('/.dockerenv'):
            return 'container'

        if 'CI' in os.environ:
            return 'ci'

        return 'development'


# ============================================================================
# MAIN CONFIGURATION ENGINE
# ============================================================================

class ConfigurationEngine:
    """
    Main configuration management engine.

    Features:
    - Multiple format support
    - Environment management
    - Schema validation
    - Secret management
    - Hot-reloading
    - Change tracking
    - Type coercion

    "Configuration is the blueprint of reality." — Ba'el
    """

    def __init__(self, config: Optional[ConfigManagerConfig] = None):
        """Initialize configuration engine."""
        self.config = config or ConfigManagerConfig()

        # Components
        self.loader = ConfigLoader()
        self.validator = ConfigValidator(self.config.validation_mode)
        self.secrets = SecretManager()
        self.environments = EnvironmentManager()

        # Configuration storage
        self._values: Dict[str, ConfigValue] = {}

        # Change tracking
        self._changes: List[ConfigChange] = []
        self._change_listeners: List[Callable[[ConfigChange], None]] = []

        # Hot reload
        self._file_watches: Dict[str, Path] = {}
        self._reload_task: Optional[asyncio.Task] = None

        logger.info("ConfigurationEngine initialized")

    # ========================================================================
    # VALUE OPERATIONS
    # ========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # Check if expired
        if key in self._values:
            config_value = self._values[key]
            if config_value.is_expired():
                del self._values[key]
            else:
                return config_value.value

        return default

    def get_value(self, key: str) -> Optional[ConfigValue]:
        """Get a configuration value with metadata."""
        return self._values.get(key)

    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.DEFAULT,
        secret: bool = False,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set a configuration value."""
        old_value = self._values.get(key)

        config_value = ConfigValue(
            key=key,
            value=value,
            source=source,
            secret=secret,
            expires_at=datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        )

        self._values[key] = config_value

        if secret:
            self.secrets.mark_secret(key)

        # Track change
        if self.config.enable_change_tracking:
            change = ConfigChange(
                key=key,
                old_value=old_value.value if old_value else None,
                new_value=value,
                source=source
            )
            self._record_change(change)

    def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        if key in self._values:
            old_value = self._values.pop(key)

            if self.config.enable_change_tracking:
                change = ConfigChange(
                    key=key,
                    old_value=old_value.value,
                    new_value=None,
                    source=ConfigSource.DEFAULT
                )
                self._record_change(change)

            return True
        return False

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return key in self._values and not self._values[key].is_expired()

    def keys(self) -> List[str]:
        """Get all configuration keys."""
        return [k for k, v in self._values.items() if not v.is_expired()]

    def all(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Get all configuration values."""
        config = {
            k: v.value for k, v in self._values.items()
            if not v.is_expired()
        }

        if not include_secrets:
            return self.secrets.mask_secrets(config)

        return config

    # ========================================================================
    # LOADING
    # ========================================================================

    def load_file(
        self,
        path: Union[str, Path],
        format: Optional[ConfigFormat] = None,
        watch: bool = False
    ) -> Dict[str, Any]:
        """Load configuration from a file."""
        path = Path(path)
        config = self.loader.load_file(path, format)

        for key, value in config.items():
            self.set(key, value, source=ConfigSource.FILE)

        if watch:
            self._file_watches[str(path)] = path
            if self.config.enable_hot_reload:
                self._ensure_reload_task()

        logger.info(f"Loaded configuration from {path}")
        return config

    def load_environment(self, prefix: str = "BAEL_") -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = self.loader.load_environment(prefix)

        for key, value in config.items():
            self.set(key, value, source=ConfigSource.ENVIRONMENT)

        logger.info(f"Loaded {len(config)} values from environment")
        return config

    def load_dict(
        self,
        config: Dict[str, Any],
        source: ConfigSource = ConfigSource.DEFAULT
    ) -> None:
        """Load configuration from a dictionary."""
        for key, value in config.items():
            self.set(key, value, source=source)

    async def load_secrets(self, keys: List[str]) -> None:
        """Load secrets for specified keys."""
        for key in keys:
            value = await self.secrets.get_secret(key)
            if value is not None:
                self.set(key, value, source=ConfigSource.SECRET_STORE, secret=True)

    # ========================================================================
    # SCHEMA VALIDATION
    # ========================================================================

    def define_schema(
        self,
        key: str,
        type: Type,
        required: bool = True,
        default: Any = None,
        **kwargs
    ) -> ConfigSchema:
        """Define a schema for a configuration key."""
        schema = ConfigSchema(
            key=key,
            type=type,
            required=required,
            default=default,
            **kwargs
        )
        self.validator.register_schema(schema)

        # Apply default if not set
        if default is not None and not self.has(key):
            self.set(key, default, source=ConfigSource.DEFAULT)

        return schema

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all configuration against schemas."""
        return self.validator.validate(self.all(include_secrets=True))

    # ========================================================================
    # ENVIRONMENTS
    # ========================================================================

    def set_environment(self, name: str) -> None:
        """Set the current environment."""
        self.environments.set_environment(name)
        env_config = self.environments.get_config()

        for key, value in env_config.items():
            self.set(key, value, source=ConfigSource.DEFAULT)

    def define_environment(
        self,
        name: str,
        config: Dict[str, Any],
        inherits_from: Optional[str] = None
    ) -> None:
        """Define an environment configuration."""
        self.environments.define_environment(name, config, inherits_from)

    # ========================================================================
    # HOT RELOAD
    # ========================================================================

    def _ensure_reload_task(self) -> None:
        """Ensure the reload task is running."""
        if self._reload_task is None or self._reload_task.done():
            self._reload_task = asyncio.create_task(self._reload_loop())

    async def _reload_loop(self) -> None:
        """Hot reload loop."""
        file_mtimes: Dict[str, float] = {}

        while True:
            await asyncio.sleep(self.config.reload_interval_seconds)

            for path_str, path in self._file_watches.items():
                try:
                    current_mtime = path.stat().st_mtime

                    if path_str in file_mtimes:
                        if current_mtime > file_mtimes[path_str]:
                            logger.info(f"Config file changed, reloading: {path}")
                            self.load_file(path, watch=False)

                    file_mtimes[path_str] = current_mtime

                except Exception as e:
                    logger.error(f"Error checking config file: {e}")

    async def stop_reload(self) -> None:
        """Stop the hot reload task."""
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass

    # ========================================================================
    # CHANGE TRACKING
    # ========================================================================

    def _record_change(self, change: ConfigChange) -> None:
        """Record a configuration change."""
        self._changes.append(change)

        # Trim history
        while len(self._changes) > self.config.max_change_history:
            self._changes.pop(0)

        # Notify listeners
        for listener in self._change_listeners:
            try:
                listener(change)
            except Exception as e:
                logger.error(f"Change listener error: {e}")

    def on_change(self, listener: Callable[[ConfigChange], None]) -> None:
        """Register a change listener."""
        self._change_listeners.append(listener)

    def get_changes(
        self,
        since: Optional[datetime] = None,
        key: Optional[str] = None
    ) -> List[ConfigChange]:
        """Get configuration changes."""
        changes = self._changes

        if since:
            changes = [c for c in changes if c.timestamp >= since]

        if key:
            changes = [c for c in changes if c.key == key]

        return changes

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def merge(self, config: Dict[str, Any], deep: bool = True) -> None:
        """Merge configuration dictionary."""
        if deep:
            current = self.all(include_secrets=True)
            self.environments._deep_merge(current, config)
            self.load_dict(current)
        else:
            self.load_dict(config)

    def freeze(self) -> Dict[str, Any]:
        """Get an immutable snapshot of configuration."""
        return copy.deepcopy(self.all(include_secrets=True))

    def export(self, format: ConfigFormat = ConfigFormat.JSON) -> str:
        """Export configuration to string."""
        config = self.all(include_secrets=False)

        if format == ConfigFormat.JSON:
            return json.dumps(config, indent=2, default=str)

        elif format == ConfigFormat.ENV:
            lines = []
            for key, value in config.items():
                if isinstance(value, bool):
                    value = str(value).lower()
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value)
                lines.append(f"{key.upper()}={value}")
            return '\n'.join(lines)

        raise ValueError(f"Export format not supported: {format}")

    def get_status(self) -> Dict[str, Any]:
        """Get configuration engine status."""
        return {
            'environment': self.environments.get_environment(),
            'total_values': len(self._values),
            'secret_count': len([v for v in self._values.values() if v.secret]),
            'expired_count': len([v for v in self._values.values() if v.is_expired()]),
            'change_count': len(self._changes),
            'watched_files': list(self._file_watches.keys()),
            'hot_reload_enabled': self.config.enable_hot_reload
        }

    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style assignment."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Dictionary-style containment check."""
        return self.has(key)


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

config_engine = ConfigurationEngine()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get(key: str, default: Any = None) -> Any:
    """Get configuration value from default engine."""
    return config_engine.get(key, default)


def set(key: str, value: Any, **kwargs) -> None:
    """Set configuration value on default engine."""
    config_engine.set(key, value, **kwargs)


def load_file(path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Load configuration file."""
    return config_engine.load_file(path, **kwargs)


def load_env(prefix: str = "BAEL_") -> Dict[str, Any]:
    """Load environment configuration."""
    return config_engine.load_environment(prefix)
