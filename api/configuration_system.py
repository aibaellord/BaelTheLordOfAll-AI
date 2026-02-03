"""
Advanced Configuration System for BAEL

Provides dynamic configuration management with environment-specific configs,
feature flags, runtime adjustments, and performance tuning parameters.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigSourceType(Enum):
    """Configuration source types"""
    FILE = "file"
    ENVIRONMENT = "environment"
    DATABASE = "database"
    REMOTE = "remote"


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    enabled: bool = False
    description: str = ""
    rollout_percentage: int = 100  # 0-100
    target_users: List[str] = field(default_factory=list)
    target_regions: List[str] = field(default_factory=list)
    enabled_from: Optional[datetime] = None
    enabled_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self, user_id: Optional[str] = None,
                  region: Optional[str] = None) -> bool:
        """Check if feature is active for user/region"""
        now = datetime.now()

        # Check time constraints
        if self.enabled_from and now < self.enabled_from:
            return False
        if self.enabled_until and now > self.enabled_until:
            return False

        if not self.enabled:
            return False

        # Check user constraints
        if self.target_users and user_id and user_id not in self.target_users:
            return False

        # Check region constraints
        if self.target_regions and region and region not in self.target_regions:
            return False

        # Check rollout percentage
        if self.rollout_percentage < 100:
            import hashlib
            hash_val = int(hashlib.md5(
                f"{user_id or 'default'}".encode()
            ).hexdigest(), 16)
            if (hash_val % 100) >= self.rollout_percentage:
                return False

        return True


@dataclass
class PerformanceTuningConfig:
    """Performance tuning parameters"""
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    batch_size: int = 100
    worker_threads: int = 4
    max_connections: int = 100
    connection_timeout_seconds: int = 30
    query_timeout_seconds: int = 60
    enable_compression: bool = True
    compression_level: int = 6  # 1-9
    enable_caching: bool = True
    cache_size_mb: int = 512
    enable_indexing: bool = True
    enable_optimization: bool = True
    optimization_interval_seconds: int = 3600


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_encryption: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    enable_tls: bool = True
    tls_version: str = "1.3"
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 1000
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 90
    enable_api_key_rotation: bool = True
    api_key_rotation_days: int = 90
    enable_threat_detection: bool = True
    threat_detection_threshold: float = 0.8


@dataclass
class DatabaseConfig:
    """Database configuration"""
    engine: str = "postgresql"  # postgresql, mysql, sqlite, mongodb
    host: str = "localhost"
    port: int = 5432
    database: str = "bael"
    username: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 3600
    echo: bool = False
    enable_replication: bool = False
    replica_hosts: List[str] = field(default_factory=list)


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    backend: str = "redis"  # redis, memcached, inmemory
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    ttl_seconds: int = 3600
    max_size_mb: int = 512
    eviction_policy: str = "lru"  # lru, lfu, fifo
    enable_compression: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "json"  # json, text
    output: str = "file"  # file, stdout, both
    log_file_path: str = "./logs/bael.log"
    max_file_size_mb: int = 100
    backup_count: int = 10
    enable_cloudwatch: bool = False
    enable_datadog: bool = False
    enable_sentry: bool = False


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_docs: bool = True
    enable_graphql: bool = False
    graphql_path: str = "/graphql"
    rest_path: str = "/api"
    api_version: str = "v1"
    rate_limiting_enabled: bool = True
    rate_limiting_window: int = 60
    rate_limiting_max_requests: int = 1000


@dataclass
class SystemConfig:
    """Master system configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    version: str = "1.0.0"
    name: str = "BAEL"

    # Sub-configurations
    performance: PerformanceTuningConfig = field(default_factory=PerformanceTuningConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # Feature flags
    feature_flags: Dict[str, FeatureFlag] = field(default_factory=dict)

    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ConfigSource(ABC):
    """Abstract configuration source"""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration"""
        pass

    @abstractmethod
    def save(self, config: Dict[str, Any]):
        """Save configuration"""
        pass


class FileConfigSource(ConfigSource):
    """Load configuration from file"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load from JSON file"""
        if not self.file_path.exists():
            logger.warning(f"Config file not found: {self.file_path}")
            return {}

        try:
            with open(self.file_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {self.file_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def save(self, config: Dict[str, Any]):
        """Save to JSON file"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            logger.info(f"Saved config to {self.file_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")


class EnvironmentConfigSource(ConfigSource):
    """Load configuration from environment variables"""

    def __init__(self, prefix: str = "BAEL_"):
        self.prefix = prefix

    def load(self) -> Dict[str, Any]:
        """Load from environment variables"""
        config = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix):].lower()
                config[config_key] = self._parse_value(value)
        logger.info(f"Loaded {len(config)} settings from environment")
        return config

    def save(self, config: Dict[str, Any]):
        """Save to environment variables"""
        for key, value in config.items():
            os.environ[f"{self.prefix}{key.upper()}"] = str(value)

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse environment variable value"""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        if value.isdigit():
            return int(value)
        if value.replace(".", "", 1).isdigit():
            return float(value)
        return value


class ConfigManager:
    """Manages system configuration"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.config = SystemConfig(environment=environment)
        self.sources: List[ConfigSource] = []
        self.watchers: List[Callable] = []
        self._update_callbacks: Dict[str, List[Callable]] = {}

    def add_source(self, source: ConfigSource):
        """Add configuration source"""
        self.sources.append(source)
        logger.info(f"Added config source: {type(source).__name__}")

    def load_config(self):
        """Load configuration from all sources"""
        merged = {}

        for source in self.sources:
            try:
                config = source.load()
                merged.update(config)
            except Exception as e:
                logger.error(f"Error loading from source: {e}")

        self._apply_config(merged)
        logger.info("Configuration loaded successfully")

    def _apply_config(self, config_dict: Dict[str, Any]):
        """Apply configuration dictionary"""
        if "environment" in config_dict:
            env_str = config_dict["environment"]
            try:
                self.config.environment = Environment(env_str)
            except ValueError:
                logger.warning(f"Invalid environment: {env_str}")

        if "performance" in config_dict:
            self._update_dataclass(self.config.performance, config_dict["performance"])
        if "security" in config_dict:
            self._update_dataclass(self.config.security, config_dict["security"])
        if "database" in config_dict:
            self._update_dataclass(self.config.database, config_dict["database"])
        if "cache" in config_dict:
            self._update_dataclass(self.config.cache, config_dict["cache"])
        if "logging" in config_dict:
            self._update_dataclass(self.config.logging, config_dict["logging"])
        if "api" in config_dict:
            self._update_dataclass(self.config.api, config_dict["api"])

        if "custom" in config_dict:
            self.config.custom_settings.update(config_dict["custom"])

        self.config.updated_at = datetime.now()

    @staticmethod
    def _update_dataclass(target, source: Dict[str, Any]):
        """Update dataclass fields from dict"""
        for key, value in source.items():
            if hasattr(target, key):
                setattr(target, key, value)

    def get_config(self) -> SystemConfig:
        """Get current configuration"""
        return self.config

    def set_setting(self, key: str, value: Any, notify: bool = True):
        """Set a configuration setting"""
        parts = key.split(".")
        target = self.config

        for part in parts[:-1]:
            if not hasattr(target, part):
                return False
            target = getattr(target, part)

        if hasattr(target, parts[-1]):
            setattr(target, parts[-1], value)
            self.config.updated_at = datetime.now()

            if notify:
                self._notify_watchers(key, value)

            logger.info(f"Updated setting: {key} = {value}")
            return True

        return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting"""
        parts = key.split(".")
        target = self.config

        for part in parts:
            if hasattr(target, part):
                target = getattr(target, part)
            else:
                return default

        return target

    def add_feature_flag(self, flag: FeatureFlag):
        """Add a feature flag"""
        self.config.feature_flags[flag.name] = flag
        logger.info(f"Added feature flag: {flag.name}")

    def is_feature_enabled(self, flag_name: str, user_id: Optional[str] = None,
                          region: Optional[str] = None) -> bool:
        """Check if feature is enabled"""
        flag = self.config.feature_flags.get(flag_name)
        if not flag:
            logger.warning(f"Feature flag not found: {flag_name}")
            return False

        return flag.is_active(user_id, region)

    def toggle_feature(self, flag_name: str, enabled: bool):
        """Toggle feature flag"""
        if flag_name in self.config.feature_flags:
            self.config.feature_flags[flag_name].enabled = enabled
            logger.info(f"Toggled feature {flag_name}: {enabled}")

    def watch_setting(self, callback: Callable):
        """Watch for configuration changes"""
        self.watchers.append(callback)

    def on_setting_changed(self, key: str, callback: Callable):
        """Register callback for specific setting change"""
        if key not in self._update_callbacks:
            self._update_callbacks[key] = []
        self._update_callbacks[key].append(callback)

    def _notify_watchers(self, key: str, value: Any):
        """Notify watchers of setting change"""
        for watcher in self.watchers:
            try:
                watcher(key, value)
            except Exception as e:
                logger.error(f"Error in watcher: {e}")

        if key in self._update_callbacks:
            for callback in self._update_callbacks[key]:
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")

    def save_config(self, source: Optional[ConfigSource] = None):
        """Save configuration to source"""
        config_dict = asdict(self.config)

        target_source = source or (self.sources[0] if self.sources else None)
        if target_source:
            target_source.save(config_dict)
            logger.info("Configuration saved")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return asdict(self.config)

    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        return {
            "environment": self.config.environment.value,
            "debug": self.config.debug,
            "version": self.config.version
        }


# Global configuration manager
_config_manager = None


def initialize_config(environment: Environment = Environment.DEVELOPMENT,
                      config_file: Optional[str] = None) -> ConfigManager:
    """Initialize global configuration manager"""
    global _config_manager

    _config_manager = ConfigManager(environment)

    # Add sources in priority order
    if config_file:
        _config_manager.add_source(FileConfigSource(config_file))

    _config_manager.add_source(EnvironmentConfigSource())

    _config_manager.load_config()

    return _config_manager


def get_config_manager() -> ConfigManager:
    """Get global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = initialize_config()
    return _config_manager


if __name__ == "__main__":
    logger.info("Configuration System initialized")
