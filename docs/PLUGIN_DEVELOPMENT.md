# BAEL Plugin Development Guide

Complete guide to creating plugins for BAEL - The Lord of All AI Agents.

## Table of Contents

1. [Overview](#overview)
2. [Plugin Types](#plugin-types)
3. [Quick Start](#quick-start)
4. [Plugin Structure](#plugin-structure)
5. [Manifest Format](#manifest-format)
6. [Plugin Interface](#plugin-interface)
7. [Sandboxing & Permissions](#sandboxing--permissions)
8. [Examples](#examples)
9. [Best Practices](#best-practices)
10. [Testing](#testing)
11. [Publishing](#publishing)

---

## Overview

BAEL's plugin system allows you to extend the system with custom:

- **Tools** - New capabilities for agents
- **Reasoning Engines** - Custom logic and decision-making
- **Integrations** - External service connections
- **Personas** - Specialized agent personalities
- **Workflows** - Process automation components

Plugins are:

- ✅ **Hot-reloadable** - Update without restarting
- ✅ **Sandboxed** - Isolated execution environment
- ✅ **Versioned** - Dependency management built-in
- ✅ **Type-safe** - Full Python type hints

---

## Plugin Types

```python
from core.plugins.registry import PluginType

PluginType.TOOL          # New tool for agents
PluginType.REASONING     # Reasoning engine
PluginType.MEMORY        # Memory system
PluginType.INTEGRATION   # External service
PluginType.PERSONA       # Agent persona
PluginType.WORKFLOW      # Workflow component
PluginType.UI            # UI component
PluginType.MIDDLEWARE    # Request/response middleware
```

---

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p plugins/my-plugin
cd plugins/my-plugin
```

### 2. Create Manifest (`plugin.yaml`)

```yaml
id: my-plugin
name: My Awesome Plugin
version: 1.0.0
description: Does something awesome
author: Your Name
license: MIT
type: tool
capabilities:
  - my_capability
dependencies: []
python_version: ">=3.8"
main_module: main.py
entry_point: register
permissions:
  - network:api.example.com
sandboxed: true
tags:
  - example
```

### 3. Create Plugin Code (`main.py`)

```python
from typing import Any, Dict
from core.plugins.registry import PluginInterface, PluginManifest

class MyPlugin(PluginInterface):
    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)

    async def initialize(self) -> bool:
        self.logger.info("✅ Plugin initialized")
        return True

    async def do_something(self, input: str) -> str:
        return f"Processed: {input}"

    async def shutdown(self):
        self.logger.info("Plugin shutdown")

def register(manifest: PluginManifest, config: Dict[str, Any]) -> MyPlugin:
    return MyPlugin(manifest, config)
```

### 4. Load Your Plugin

```python
from pathlib import Path
from core.plugins.registry import PluginRegistry

registry = PluginRegistry(Path("plugins"))
await registry.load_plugin("my-plugin")

plugin = registry.get_plugin("my-plugin")
result = await plugin.do_something("Hello!")
```

---

## Plugin Structure

```
my-plugin/
├── plugin.yaml          # Manifest (required)
├── main.py             # Main plugin code (required)
├── README.md           # Documentation (recommended)
├── requirements.txt    # Python dependencies (optional)
├── tests/              # Unit tests (recommended)
│   └── test_plugin.py
└── examples/           # Usage examples (optional)
    └── example.py
```

---

## Manifest Format

### Required Fields

```yaml
id: unique-plugin-id
name: Human Readable Name
version: 1.0.0
description: What the plugin does
type: tool # tool, reasoning, memory, integration, persona, workflow, ui, middleware
main_module: main.py
entry_point: register
```

### Optional Fields

```yaml
# Metadata
author: Your Name
license: MIT
homepage: https://github.com/user/plugin
repository: https://github.com/user/plugin.git
tags:
  - tag1
  - tag2

# Capabilities
capabilities:
  - capability1
  - capability2

# Dependencies
dependencies:
  - name: requests
    version: ">=2.31.0"
    optional: false
  - name: beautifulsoup4
    version: ">=4.9.0"
    optional: true

# Python version
python_version: ">=3.8"

# Configuration schema
config_schema:
  api_key:
    type: string
    required: true
    description: API key for service
  timeout:
    type: number
    required: false
    default: 30

# Default configuration
default_config:
  timeout: 30
  retries: 3

# Permissions
permissions:
  - network:api.example.com
  - network:*.example.com
  - filesystem:/tmp/my-plugin
  - api:brain
  - api:memory

# Sandboxing
sandboxed: true
```

---

## Plugin Interface

All plugins must implement `PluginInterface`:

```python
class PluginInterface:
    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = logging.getLogger(f"BAEL.Plugin.{manifest.name}")

    async def initialize(self) -> bool:
        """Initialize plugin. Return True if successful."""
        raise NotImplementedError

    async def shutdown(self):
        """Cleanup resources."""
        pass

    async def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return self.manifest.to_dict()
```

### Lifecycle

1. **Load** - Plugin module imported
2. **Register** - Entry point called, instance created
3. **Initialize** - `initialize()` called
4. **Active** - Plugin available for use
5. **Shutdown** - `shutdown()` called
6. **Unload** - Plugin removed

---

## Sandboxing & Permissions

### Permission Types

```yaml
# Network access
permissions:
  - network:*                    # All domains
  - network:api.example.com      # Specific domain
  - network:*.example.com        # Wildcard subdomain

# Filesystem access
permissions:
  - filesystem:/tmp/my-plugin    # Specific directory
  - filesystem:/data/*           # Pattern matching

# API access
permissions:
  - api:*                        # All BAEL APIs
  - api:brain                    # Brain API
  - api:memory                   # Memory API
  - api:tools                    # Tool registry
```

### Sandbox Enforcement

```python
from core.plugins.registry import PluginSandbox

sandbox = PluginSandbox("my-plugin", permissions)

# Check permissions
if sandbox.check_network_access("api.example.com"):
    # Allowed
    make_request()

if sandbox.check_filesystem_access(Path("/tmp/data")):
    # Allowed
    read_file()
```

---

## Examples

### Example 1: Simple Tool Plugin

```python
# plugins/calculator/calculator.py

class Calculator(PluginInterface):
    async def initialize(self) -> bool:
        return True

    def add(self, a: float, b: float) -> float:
        return a + b

    def multiply(self, a: float, b: float) -> float:
        return a * b

def register(manifest, config):
    return Calculator(manifest, config)
```

### Example 2: API Integration Plugin

```python
# plugins/weather/weather.py

import aiohttp

class WeatherPlugin(PluginInterface):
    async def initialize(self) -> bool:
        self.api_key = self.config.get("api_key")
        self.session = aiohttp.ClientSession()
        return self.api_key is not None

    async def get_weather(self, city: str) -> Dict:
        async with self.session.get(
            f"https://api.weather.com/weather?q={city}&key={self.api_key}"
        ) as resp:
            return await resp.json()

    async def shutdown(self):
        await self.session.close()

def register(manifest, config):
    return WeatherPlugin(manifest, config)
```

### Example 3: Reasoning Engine Plugin

```python
# plugins/sentiment/sentiment.py

class SentimentAnalyzer(PluginInterface):
    async def initialize(self) -> bool:
        self.positive_words = set(["good", "great", "excellent"])
        self.negative_words = set(["bad", "terrible", "awful"])
        return True

    def analyze(self, text: str) -> Dict:
        words = text.lower().split()
        pos_count = sum(1 for w in words if w in self.positive_words)
        neg_count = sum(1 for w in words if w in self.negative_words)

        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "positive_count": pos_count,
            "negative_count": neg_count
        }

def register(manifest, config):
    return SentimentAnalyzer(manifest, config)
```

---

## Best Practices

### 1. Error Handling

```python
class MyPlugin(PluginInterface):
    async def initialize(self) -> bool:
        try:
            # Initialization code
            self.setup()
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def my_method(self):
        try:
            # Operation
            result = self.do_work()
            return result
        except Exception as e:
            self.logger.error(f"Operation failed: {e}")
            return {"error": str(e)}
```

### 2. Configuration Validation

```python
async def initialize(self) -> bool:
    required_keys = ["api_key", "endpoint"]
    for key in required_keys:
        if key not in self.config:
            self.logger.error(f"Missing required config: {key}")
            return False

    if not self.config["api_key"]:
        self.logger.error("API key is empty")
        return False

    return True
```

### 3. Resource Management

```python
class MyPlugin(PluginInterface):
    async def initialize(self) -> bool:
        self.session = aiohttp.ClientSession()
        self.connection = await self.connect_db()
        return True

    async def shutdown(self):
        if self.session:
            await self.session.close()
        if self.connection:
            await self.connection.close()
        self.logger.info("Resources cleaned up")
```

### 4. Logging

```python
class MyPlugin(PluginInterface):
    def my_method(self, input: str):
        self.logger.debug(f"Processing input: {input}")

        result = self.process(input)

        self.logger.info(f"Processed successfully")
        return result
```

### 5. Type Hints

```python
from typing import Dict, List, Optional, Any

class MyPlugin(PluginInterface):
    async def initialize(self) -> bool:
        return True

    def process(
        self,
        data: Dict[str, Any],
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return {"result": "success"}
```

---

## Testing

### Unit Tests

```python
# tests/test_my_plugin.py

import pytest
from core.plugins.registry import PluginManifest
from plugins.my_plugin.main import MyPlugin

@pytest.fixture
def plugin():
    manifest = PluginManifest(
        id="test-plugin",
        name="Test",
        version="1.0.0",
        description="Test plugin",
        type="tool"
    )
    config = {"api_key": "test_key"}
    return MyPlugin(manifest, config)

@pytest.mark.asyncio
async def test_initialize(plugin):
    assert await plugin.initialize() == True

@pytest.mark.asyncio
async def test_my_method(plugin):
    await plugin.initialize()
    result = await plugin.my_method("test")
    assert result is not None
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_plugin_loading():
    from core.plugins.registry import PluginRegistry
    from pathlib import Path

    registry = PluginRegistry(Path("plugins"))

    success = await registry.load_plugin("my-plugin")
    assert success == True

    plugin = registry.get_plugin("my-plugin")
    assert plugin is not None

    result = await plugin.my_method("test")
    assert result["success"] == True
```

---

## Publishing

### 1. Prepare for Release

```bash
# Create distribution
tar -czf my-plugin-1.0.0.tar.gz my-plugin/

# Or use git
git tag v1.0.0
git push origin v1.0.0
```

### 2. Documentation

Create comprehensive `README.md`:

- Installation instructions
- Configuration guide
- API reference
- Usage examples
- Troubleshooting

### 3. Share

- GitHub repository
- BAEL plugin marketplace (coming soon)
- PyPI package (for dependencies)

---

## Example Plugins

See the `plugins/` directory for working examples:

1. **[weather-tool](../plugins/weather-tool/)** - Fetches weather data
2. **[sentiment-analyzer](../plugins/sentiment-analyzer/)** - Analyzes text sentiment
3. **[github-integration](../plugins/github-integration/)** - GitHub API integration

---

## Support

- 📖 Documentation: https://docs.bael.ai/plugins
- 💬 Discord: https://discord.gg/bael
- 🐛 Issues: https://github.com/bael/bael/issues
- 📧 Email: plugins@bael.ai

---

## License

This guide is part of BAEL and is licensed under MIT.
