#!/usr/bin/env python3
"""
BAEL - Environment Engine
Environment modeling and management for agents.

Features:
- Environment state modeling
- Variable management
- Configuration loading
- Environment switching
- Resource tracking
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

class EnvType(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    LOCAL = "local"


class VariableSource(Enum):
    """Variable sources."""
    ENV = "env"
    FILE = "file"
    DEFAULT = "default"
    RUNTIME = "runtime"
    REMOTE = "remote"


class ResourceType(Enum):
    """Resource types."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"


class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    ENV = "env"
    YAML = "yaml"
    INI = "ini"


class VariableType(Enum):
    """Variable value types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class EnvVariable:
    """An environment variable."""
    name: str = ""
    value: Any = None
    source: VariableSource = VariableSource.DEFAULT
    var_type: VariableType = VariableType.STRING
    secret: bool = False
    description: str = ""
    set_at: datetime = field(default_factory=datetime.now)


@dataclass
class Environment:
    """An environment configuration."""
    env_id: str = ""
    name: str = ""
    env_type: EnvType = EnvType.DEVELOPMENT
    variables: Dict[str, EnvVariable] = field(default_factory=dict)
    parent: Optional[str] = None
    active: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.env_id:
            self.env_id = str(uuid.uuid4())[:8]


@dataclass
class ResourceLimit:
    """Resource limits."""
    resource_type: ResourceType = ResourceType.CPU
    limit: float = 0.0
    current: float = 0.0
    unit: str = ""


@dataclass
class EnvConfig:
    """Environment engine configuration."""
    default_env: EnvType = EnvType.DEVELOPMENT
    auto_load_env: bool = True
    env_file: str = ".env"
    expand_vars: bool = True


# =============================================================================
# VARIABLE PARSER
# =============================================================================

class VariableParser:
    """Parse and convert variable values."""

    TRUE_VALUES = {"true", "1", "yes", "on", "enabled"}
    FALSE_VALUES = {"false", "0", "no", "off", "disabled"}

    def parse(self, value: str, var_type: VariableType) -> Any:
        """Parse string value to type."""
        if value is None:
            return None

        if var_type == VariableType.STRING:
            return str(value)

        elif var_type == VariableType.INTEGER:
            return int(value)

        elif var_type == VariableType.FLOAT:
            return float(value)

        elif var_type == VariableType.BOOLEAN:
            if isinstance(value, bool):
                return value
            return str(value).lower() in self.TRUE_VALUES

        elif var_type == VariableType.LIST:
            if isinstance(value, list):
                return value
            return [v.strip() for v in str(value).split(",")]

        elif var_type == VariableType.DICT:
            if isinstance(value, dict):
                return value
            return json.loads(value)

        return value

    def detect_type(self, value: str) -> VariableType:
        """Detect variable type from value."""
        if value is None:
            return VariableType.STRING

        lower = str(value).lower()

        if lower in self.TRUE_VALUES or lower in self.FALSE_VALUES:
            return VariableType.BOOLEAN

        try:
            int(value)
            return VariableType.INTEGER
        except ValueError:
            pass

        try:
            float(value)
            return VariableType.FLOAT
        except ValueError:
            pass

        if value.startswith("[") or value.startswith("{"):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return VariableType.LIST
                elif isinstance(parsed, dict):
                    return VariableType.DICT
            except json.JSONDecodeError:
                pass

        return VariableType.STRING

    def stringify(self, value: Any, var_type: VariableType) -> str:
        """Convert value to string."""
        if value is None:
            return ""

        if var_type in (VariableType.LIST, VariableType.DICT):
            return json.dumps(value)

        if var_type == VariableType.BOOLEAN:
            return "true" if value else "false"

        return str(value)


# =============================================================================
# CONFIG LOADER
# =============================================================================

class ConfigLoader:
    """Load configuration from files."""

    def __init__(self):
        self._parser = VariableParser()

    def load_env_file(self, path: Path) -> Dict[str, str]:
        """Load .env file."""
        variables = {}

        if not path.exists():
            return variables

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

                    variables[key] = value

        return variables

    def load_json_file(self, path: Path) -> Dict[str, Any]:
        """Load JSON config file."""
        if not path.exists():
            return {}

        with open(path, "r") as f:
            return json.load(f)

    def load(self, path: Path) -> Dict[str, Any]:
        """Load config file based on extension."""
        suffix = path.suffix.lower()

        if suffix == ".env" or path.name.startswith(".env"):
            return self.load_env_file(path)
        elif suffix == ".json":
            return self.load_json_file(path)

        return {}


# =============================================================================
# VARIABLE MANAGER
# =============================================================================

class VariableManager:
    """Manage environment variables."""

    def __init__(self, expand_vars: bool = True):
        self._variables: Dict[str, EnvVariable] = {}
        self._parser = VariableParser()
        self._expand_vars = expand_vars

        self._var_pattern = re.compile(r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)')

    def set(
        self,
        name: str,
        value: Any,
        source: VariableSource = VariableSource.RUNTIME,
        var_type: Optional[VariableType] = None,
        secret: bool = False,
        description: str = ""
    ) -> EnvVariable:
        """Set a variable."""
        if var_type is None:
            var_type = self._parser.detect_type(str(value))

        parsed_value = self._parser.parse(value, var_type)

        variable = EnvVariable(
            name=name,
            value=parsed_value,
            source=source,
            var_type=var_type,
            secret=secret,
            description=description
        )

        self._variables[name] = variable

        return variable

    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        variable = self._variables.get(name)

        if variable is None:
            return default

        value = variable.value

        if self._expand_vars and isinstance(value, str):
            value = self._expand(value)

        return value

    def get_variable(self, name: str) -> Optional[EnvVariable]:
        """Get variable object."""
        return self._variables.get(name)

    def _expand(self, value: str) -> str:
        """Expand variable references."""
        def replacer(match):
            var_name = match.group(1) or match.group(2)
            return str(self.get(var_name, match.group(0)))

        return self._var_pattern.sub(replacer, value)

    def delete(self, name: str) -> bool:
        """Delete a variable."""
        if name in self._variables:
            del self._variables[name]
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if variable exists."""
        return name in self._variables

    def get_by_source(self, source: VariableSource) -> List[EnvVariable]:
        """Get variables by source."""
        return [v for v in self._variables.values() if v.source == source]

    def get_secrets(self) -> List[str]:
        """Get secret variable names."""
        return [v.name for v in self._variables.values() if v.secret]

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export variables as dictionary."""
        result = {}

        for name, var in self._variables.items():
            if var.secret and not include_secrets:
                result[name] = "***"
            else:
                result[name] = var.value

        return result

    def from_dict(
        self,
        data: Dict[str, Any],
        source: VariableSource = VariableSource.RUNTIME
    ) -> int:
        """Import variables from dictionary."""
        count = 0

        for name, value in data.items():
            self.set(name, value, source)
            count += 1

        return count

    def count(self) -> int:
        """Count variables."""
        return len(self._variables)

    def all(self) -> List[EnvVariable]:
        """Get all variables."""
        return list(self._variables.values())

    def clear(self) -> int:
        """Clear all variables."""
        count = len(self._variables)
        self._variables.clear()
        return count


# =============================================================================
# ENVIRONMENT MANAGER
# =============================================================================

class EnvironmentManager:
    """Manage multiple environments."""

    def __init__(self):
        self._environments: Dict[str, Environment] = {}
        self._active: Optional[str] = None

    def create(
        self,
        name: str,
        env_type: EnvType = EnvType.DEVELOPMENT,
        parent: Optional[str] = None
    ) -> Environment:
        """Create a new environment."""
        env = Environment(
            name=name,
            env_type=env_type,
            parent=parent
        )

        self._environments[env.env_id] = env

        return env

    def get(self, env_id: str) -> Optional[Environment]:
        """Get environment by ID."""
        return self._environments.get(env_id)

    def get_by_name(self, name: str) -> Optional[Environment]:
        """Get environment by name."""
        for env in self._environments.values():
            if env.name == name:
                return env
        return None

    def get_by_type(self, env_type: EnvType) -> List[Environment]:
        """Get environments by type."""
        return [e for e in self._environments.values() if e.env_type == env_type]

    def activate(self, env_id: str) -> bool:
        """Activate an environment."""
        env = self._environments.get(env_id)

        if not env:
            return False

        if self._active:
            active_env = self._environments.get(self._active)
            if active_env:
                active_env.active = False

        env.active = True
        self._active = env_id

        return True

    def get_active(self) -> Optional[Environment]:
        """Get active environment."""
        if self._active:
            return self._environments.get(self._active)
        return None

    def deactivate(self) -> bool:
        """Deactivate current environment."""
        if self._active:
            env = self._environments.get(self._active)
            if env:
                env.active = False
            self._active = None
            return True
        return False

    def delete(self, env_id: str) -> bool:
        """Delete an environment."""
        if env_id in self._environments:
            if self._active == env_id:
                self._active = None
            del self._environments[env_id]
            return True
        return False

    def count(self) -> int:
        """Count environments."""
        return len(self._environments)

    def all(self) -> List[Environment]:
        """Get all environments."""
        return list(self._environments.values())


# =============================================================================
# RESOURCE TRACKER
# =============================================================================

class ResourceTracker:
    """Track resource usage."""

    def __init__(self):
        self._limits: Dict[ResourceType, ResourceLimit] = {}
        self._usage: Dict[ResourceType, List[Tuple[datetime, float]]] = defaultdict(list)

    def set_limit(
        self,
        resource_type: ResourceType,
        limit: float,
        unit: str = ""
    ) -> ResourceLimit:
        """Set resource limit."""
        resource = ResourceLimit(
            resource_type=resource_type,
            limit=limit,
            unit=unit
        )

        self._limits[resource_type] = resource

        return resource

    def record_usage(
        self,
        resource_type: ResourceType,
        value: float
    ) -> None:
        """Record resource usage."""
        self._usage[resource_type].append((datetime.now(), value))

        if resource_type in self._limits:
            self._limits[resource_type].current = value

    def get_usage(
        self,
        resource_type: ResourceType,
        since: Optional[datetime] = None
    ) -> List[Tuple[datetime, float]]:
        """Get usage history."""
        usage = self._usage.get(resource_type, [])

        if since:
            return [(ts, val) for ts, val in usage if ts >= since]

        return list(usage)

    def get_current(self, resource_type: ResourceType) -> float:
        """Get current usage."""
        if resource_type in self._limits:
            return self._limits[resource_type].current

        usage = self._usage.get(resource_type, [])
        if usage:
            return usage[-1][1]

        return 0.0

    def check_limit(self, resource_type: ResourceType) -> Tuple[bool, float]:
        """Check if within limit."""
        limit = self._limits.get(resource_type)

        if not limit:
            return True, 0.0

        current = self.get_current(resource_type)
        remaining = limit.limit - current

        return current <= limit.limit, remaining

    def get_all_limits(self) -> Dict[ResourceType, ResourceLimit]:
        """Get all resource limits."""
        return dict(self._limits)


# =============================================================================
# ENVIRONMENT ENGINE
# =============================================================================

class EnvironmentEngine:
    """
    Environment Engine for BAEL.

    Environment modeling and management.
    """

    def __init__(self, config: Optional[EnvConfig] = None):
        self._config = config or EnvConfig()

        self._variable_manager = VariableManager(self._config.expand_vars)
        self._env_manager = EnvironmentManager()
        self._resource_tracker = ResourceTracker()
        self._config_loader = ConfigLoader()

        if self._config.auto_load_env:
            self._load_system_env()

    def _load_system_env(self) -> None:
        """Load system environment variables."""
        for name, value in os.environ.items():
            self._variable_manager.set(
                name, value, VariableSource.ENV
            )

    # ----- Variable Operations -----

    def set(
        self,
        name: str,
        value: Any,
        secret: bool = False
    ) -> EnvVariable:
        """Set a variable."""
        return self._variable_manager.set(
            name, value, VariableSource.RUNTIME, secret=secret
        )

    def get(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self._variable_manager.get(name, default)

    def get_int(self, name: str, default: int = 0) -> int:
        """Get integer variable."""
        value = self.get(name)
        if value is None:
            return default
        return int(value)

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get float variable."""
        value = self.get(name)
        if value is None:
            return default
        return float(value)

    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get boolean variable."""
        value = self.get(name)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def get_list(self, name: str, default: Optional[List] = None) -> List:
        """Get list variable."""
        value = self.get(name)
        if value is None:
            return default or []
        if isinstance(value, list):
            return value
        return [v.strip() for v in str(value).split(",")]

    def delete(self, name: str) -> bool:
        """Delete a variable."""
        return self._variable_manager.delete(name)

    def exists(self, name: str) -> bool:
        """Check if variable exists."""
        return self._variable_manager.exists(name)

    # ----- Config File Operations -----

    def load_file(self, path: str) -> int:
        """Load variables from file."""
        data = self._config_loader.load(Path(path))
        return self._variable_manager.from_dict(data, VariableSource.FILE)

    def load_env_file(self, path: str = ".env") -> int:
        """Load .env file."""
        data = self._config_loader.load_env_file(Path(path))
        return self._variable_manager.from_dict(data, VariableSource.FILE)

    # ----- Environment Operations -----

    def create_env(
        self,
        name: str,
        env_type: EnvType = EnvType.DEVELOPMENT
    ) -> Environment:
        """Create an environment."""
        return self._env_manager.create(name, env_type)

    def get_env(self, name: str) -> Optional[Environment]:
        """Get environment by name."""
        return self._env_manager.get_by_name(name)

    def activate_env(self, name: str) -> bool:
        """Activate an environment."""
        env = self._env_manager.get_by_name(name)
        if env:
            return self._env_manager.activate(env.env_id)
        return False

    def get_active_env(self) -> Optional[Environment]:
        """Get active environment."""
        return self._env_manager.get_active()

    def is_production(self) -> bool:
        """Check if production environment."""
        env = self.get_active_env()
        return env and env.env_type == EnvType.PRODUCTION

    def is_development(self) -> bool:
        """Check if development environment."""
        env = self.get_active_env()
        return env and env.env_type == EnvType.DEVELOPMENT

    # ----- Resource Operations -----

    def set_resource_limit(
        self,
        resource_type: ResourceType,
        limit: float,
        unit: str = ""
    ) -> ResourceLimit:
        """Set resource limit."""
        return self._resource_tracker.set_limit(resource_type, limit, unit)

    def record_resource_usage(
        self,
        resource_type: ResourceType,
        value: float
    ) -> None:
        """Record resource usage."""
        self._resource_tracker.record_usage(resource_type, value)

    def check_resource(
        self,
        resource_type: ResourceType
    ) -> Tuple[bool, float]:
        """Check if resource within limit."""
        return self._resource_tracker.check_limit(resource_type)

    def get_resource_usage(
        self,
        resource_type: ResourceType
    ) -> float:
        """Get current resource usage."""
        return self._resource_tracker.get_current(resource_type)

    # ----- Export/Import -----

    def export_vars(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export all variables."""
        return self._variable_manager.to_dict(include_secrets)

    def import_vars(self, data: Dict[str, Any]) -> int:
        """Import variables."""
        return self._variable_manager.from_dict(data)

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        active_env = self.get_active_env()

        return {
            "variables": self._variable_manager.count(),
            "secrets": len(self._variable_manager.get_secrets()),
            "environments": self._env_manager.count(),
            "active_env": active_env.name if active_env else None,
            "env_type": active_env.env_type.value if active_env else None,
            "resource_limits": len(self._resource_tracker.get_all_limits())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Environment Engine."""
    print("=" * 70)
    print("BAEL - ENVIRONMENT ENGINE DEMO")
    print("Environment Modeling and Management")
    print("=" * 70)
    print()

    engine = EnvironmentEngine(EnvConfig(auto_load_env=False))

    # 1. Set Variables
    print("1. SET VARIABLES:")
    print("-" * 40)

    engine.set("APP_NAME", "BAEL")
    engine.set("DEBUG", "true")
    engine.set("MAX_WORKERS", "8")
    engine.set("RATE_LIMIT", "100.5")
    engine.set("API_KEY", "secret-key-123", secret=True)

    print(f"   APP_NAME: {engine.get('APP_NAME')}")
    print(f"   DEBUG: {engine.get('DEBUG')}")
    print(f"   MAX_WORKERS: {engine.get('MAX_WORKERS')}")
    print()

    # 2. Typed Getters
    print("2. TYPED GETTERS:")
    print("-" * 40)

    print(f"   get_bool('DEBUG'): {engine.get_bool('DEBUG')} ({type(engine.get_bool('DEBUG')).__name__})")
    print(f"   get_int('MAX_WORKERS'): {engine.get_int('MAX_WORKERS')} ({type(engine.get_int('MAX_WORKERS')).__name__})")
    print(f"   get_float('RATE_LIMIT'): {engine.get_float('RATE_LIMIT')} ({type(engine.get_float('RATE_LIMIT')).__name__})")
    print()

    # 3. Default Values
    print("3. DEFAULT VALUES:")
    print("-" * 40)

    print(f"   get('MISSING'): {engine.get('MISSING')}")
    print(f"   get('MISSING', 'default'): {engine.get('MISSING', 'default')}")
    print(f"   get_int('MISSING', 42): {engine.get_int('MISSING', 42)}")
    print()

    # 4. Variable Expansion
    print("4. VARIABLE EXPANSION:")
    print("-" * 40)

    engine.set("BASE_URL", "https://api.example.com")
    engine.set("ENDPOINT", "${BASE_URL}/v1/users")

    print(f"   BASE_URL: {engine.get('BASE_URL')}")
    print(f"   ENDPOINT (expanded): {engine.get('ENDPOINT')}")
    print()

    # 5. List Variables
    print("5. LIST VARIABLES:")
    print("-" * 40)

    engine.set("ALLOWED_HOSTS", "localhost,127.0.0.1,example.com")

    hosts = engine.get_list("ALLOWED_HOSTS")
    print(f"   ALLOWED_HOSTS: {hosts}")
    print(f"   Type: {type(hosts).__name__}")
    print()

    # 6. Create Environments
    print("6. CREATE ENVIRONMENTS:")
    print("-" * 40)

    dev_env = engine.create_env("development", EnvType.DEVELOPMENT)
    staging_env = engine.create_env("staging", EnvType.STAGING)
    prod_env = engine.create_env("production", EnvType.PRODUCTION)

    print(f"   Created: {dev_env.name} ({dev_env.env_type.value})")
    print(f"   Created: {staging_env.name} ({staging_env.env_type.value})")
    print(f"   Created: {prod_env.name} ({prod_env.env_type.value})")
    print()

    # 7. Activate Environment
    print("7. ACTIVATE ENVIRONMENT:")
    print("-" * 40)

    engine.activate_env("development")
    active = engine.get_active_env()

    print(f"   Active: {active.name if active else 'None'}")
    print(f"   Is Development: {engine.is_development()}")
    print(f"   Is Production: {engine.is_production()}")

    engine.activate_env("production")
    print(f"   After switch to production:")
    print(f"   Is Development: {engine.is_development()}")
    print(f"   Is Production: {engine.is_production()}")
    print()

    # 8. Resource Limits
    print("8. RESOURCE LIMITS:")
    print("-" * 40)

    engine.set_resource_limit(ResourceType.CPU, 80.0, "%")
    engine.set_resource_limit(ResourceType.MEMORY, 1024.0, "MB")

    engine.record_resource_usage(ResourceType.CPU, 45.0)
    engine.record_resource_usage(ResourceType.MEMORY, 512.0)

    cpu_ok, cpu_remaining = engine.check_resource(ResourceType.CPU)
    mem_ok, mem_remaining = engine.check_resource(ResourceType.MEMORY)

    print(f"   CPU: {engine.get_resource_usage(ResourceType.CPU)}% (limit: 80%)")
    print(f"   CPU OK: {cpu_ok}, remaining: {cpu_remaining}%")
    print(f"   Memory: {engine.get_resource_usage(ResourceType.MEMORY)}MB (limit: 1024MB)")
    print(f"   Memory OK: {mem_ok}, remaining: {mem_remaining}MB")
    print()

    # 9. Export Variables
    print("9. EXPORT VARIABLES:")
    print("-" * 40)

    exported = engine.export_vars(include_secrets=False)

    for key, value in list(exported.items())[:5]:
        print(f"   {key}: {value}")
    print(f"   ... and {len(exported) - 5} more")
    print()

    # 10. Secret Handling
    print("10. SECRET HANDLING:")
    print("-" * 40)

    print(f"   API_KEY (no secrets): {engine.export_vars()['API_KEY']}")
    print(f"   API_KEY (with secrets): {engine.export_vars(include_secrets=True)['API_KEY']}")
    print()

    # 11. Check Existence
    print("11. CHECK EXISTENCE:")
    print("-" * 40)

    print(f"   exists('APP_NAME'): {engine.exists('APP_NAME')}")
    print(f"   exists('NONEXISTENT'): {engine.exists('NONEXISTENT')}")
    print()

    # 12. Delete Variables
    print("12. DELETE VARIABLES:")
    print("-" * 40)

    engine.set("TEMP_VAR", "temporary")
    print(f"   TEMP_VAR before delete: {engine.get('TEMP_VAR')}")

    engine.delete("TEMP_VAR")
    print(f"   TEMP_VAR after delete: {engine.get('TEMP_VAR')}")
    print()

    # 13. Import Variables
    print("13. IMPORT VARIABLES:")
    print("-" * 40)

    new_vars = {
        "IMPORTED_1": "value1",
        "IMPORTED_2": "value2",
        "IMPORTED_3": "value3"
    }

    count = engine.import_vars(new_vars)
    print(f"   Imported {count} variables")
    print(f"   IMPORTED_1: {engine.get('IMPORTED_1')}")
    print()

    # 14. Environment Info
    print("14. ENVIRONMENT INFO:")
    print("-" * 40)

    active = engine.get_active_env()
    if active:
        print(f"   ID: {active.env_id}")
        print(f"   Name: {active.name}")
        print(f"   Type: {active.env_type.value}")
        print(f"   Active: {active.active}")
        print(f"   Created: {active.created_at.isoformat()}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Environment Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
