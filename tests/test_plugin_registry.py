"""
Unit tests for core.plugins.registry module
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

import pytest

from core.plugins.registry import (PluginConfigError, PluginDependency,
                                   PluginError, PluginInterface, PluginLoader,
                                   PluginLoadError, PluginManifest,
                                   PluginRegistry, PluginSandbox, PluginType)


class MockPlugin(PluginInterface):
    """Mock plugin for testing"""

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)
        self.initialized = False

    async def initialize(self) -> bool:
        self.initialized = True
        return True

    async def shutdown(self):
        self.initialized = False

    async def test_method(self, value: str) -> str:
        return f"processed: {value}"


class TestPluginManifest:
    """Test PluginManifest class"""

    def test_create_minimal_manifest(self):
        """Test creating minimal manifest"""

        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        assert manifest.id == "test-plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.type == PluginType.TOOL

    def test_create_full_manifest(self):
        """Test creating complete manifest"""

        manifest = PluginManifest(
            id="full-plugin",
            name="Full Plugin",
            version="2.0.0",
            description="Complete manifest",
            author="Test Author",
            license="MIT",
            type=PluginType.INTEGRATION,
            capabilities=["api", "data"],
            dependencies=[
                PluginDependency(
                    name="requests",
                    version=">=2.31.0",
                    optional=False
                )
            ],
            permissions=["network:api.example.com"],
            config_schema={
                "api_key": {"type": "string", "required": True}
            },
            tags=["api", "integration"]
        )

        assert manifest.author == "Test Author"
        assert len(manifest.capabilities) == 2
        assert len(manifest.dependencies) == 1
        assert len(manifest.permissions) == 1

    def test_manifest_to_dict(self):
        """Test converting manifest to dictionary"""

        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        manifest_dict = manifest.to_dict()

        assert manifest_dict["id"] == "test"
        assert manifest_dict["type"] == "TOOL"
        assert "created_at" in manifest_dict


class TestPluginDependency:
    """Test PluginDependency class"""

    def test_create_dependency(self):
        """Test creating dependency"""

        dep = PluginDependency(
            name="requests",
            version=">=2.31.0",
            optional=False
        )

        assert dep.name == "requests"
        assert dep.version == ">=2.31.0"
        assert dep.optional == False

    def test_optional_dependency(self):
        """Test optional dependency"""

        dep = PluginDependency(
            name="optional-package",
            version=">=1.0.0",
            optional=True
        )

        assert dep.optional == True


class TestPluginSandbox:
    """Test PluginSandbox class"""

    def test_create_sandbox(self):
        """Test creating sandbox"""

        sandbox = PluginSandbox(
            plugin_id="test-plugin",
            permissions=["network:api.example.com"]
        )

        assert sandbox.plugin_id == "test-plugin"
        assert len(sandbox.permissions) == 1

    def test_check_network_access_allowed(self):
        """Test checking allowed network access"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["network:api.example.com"]
        )

        assert sandbox.check_network_access("api.example.com") == True

    def test_check_network_access_denied(self):
        """Test checking denied network access"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["network:api.example.com"]
        )

        assert sandbox.check_network_access("other.com") == False

    def test_check_wildcard_network_access(self):
        """Test wildcard network permissions"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["network:*.example.com"]
        )

        assert sandbox.check_network_access("api.example.com") == True
        assert sandbox.check_network_access("data.example.com") == True
        assert sandbox.check_network_access("other.com") == False

    def test_check_filesystem_access_allowed(self):
        """Test checking allowed filesystem access"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["filesystem:/tmp/plugin-data"]
        )

        assert sandbox.check_filesystem_access(Path("/tmp/plugin-data")) == True
        assert sandbox.check_filesystem_access(Path("/tmp/plugin-data/file.txt")) == True

    def test_check_filesystem_access_denied(self):
        """Test checking denied filesystem access"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["filesystem:/tmp/plugin-data"]
        )

        assert sandbox.check_filesystem_access(Path("/etc/passwd")) == False
        assert sandbox.check_filesystem_access(Path("/home/user")) == False

    def test_check_api_access(self):
        """Test checking API access"""

        sandbox = PluginSandbox(
            plugin_id="test",
            permissions=["api:brain", "api:memory"]
        )

        assert sandbox.check_api_access("brain") == True
        assert sandbox.check_api_access("memory") == True
        assert sandbox.check_api_access("tools") == False


class TestPluginLoader:
    """Test PluginLoader class"""

    def test_create_loader(self):
        """Test creating plugin loader"""

        loader = PluginLoader(Path("plugins"))

        assert loader.plugin_dir == Path("plugins")

    def test_validate_manifest_valid(self):
        """Test validating valid manifest"""

        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test plugin",
            type=PluginType.TOOL
        )

        loader = PluginLoader(Path("plugins"))

        # Should not raise exception
        loader.validate_manifest(manifest)

    def test_validate_manifest_invalid(self):
        """Test validating invalid manifest"""

        # Missing required fields
        with pytest.raises((PluginError, TypeError)):
            manifest = PluginManifest(
                id="",  # Invalid empty ID
                name="Test",
                version="1.0.0",
                description="Test",
                type=PluginType.TOOL
            )


class TestPluginRegistry:
    """Test PluginRegistry class"""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create temporary plugin registry"""
        return PluginRegistry(tmp_path)

    def test_create_registry(self, tmp_path):
        """Test creating plugin registry"""

        registry = PluginRegistry(tmp_path)

        assert registry.plugin_dir == tmp_path
        assert len(registry.plugins) == 0

    def test_register_plugin(self, registry):
        """Test registering plugin manually"""

        manifest = PluginManifest(
            id="manual-plugin",
            name="Manual Plugin",
            version="1.0.0",
            description="Manually registered",
            type=PluginType.TOOL
        )

        plugin = MockPlugin(manifest, {})
        registry.register_plugin("manual-plugin", plugin, manifest)

        assert "manual-plugin" in registry.plugins
        assert registry.get_plugin("manual-plugin") == plugin

    def test_get_plugin(self, registry):
        """Test getting plugin by ID"""

        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        plugin = MockPlugin(manifest, {})
        registry.register_plugin("test", plugin, manifest)

        retrieved = registry.get_plugin("test")
        assert retrieved == plugin

    def test_get_nonexistent_plugin(self, registry):
        """Test getting non-existent plugin"""

        plugin = registry.get_plugin("nonexistent")
        assert plugin is None

    def test_list_plugins(self, registry):
        """Test listing all plugins"""

        # Register multiple plugins
        for i in range(3):
            manifest = PluginManifest(
                id=f"plugin-{i}",
                name=f"Plugin {i}",
                version="1.0.0",
                description=f"Test plugin {i}",
                type=PluginType.TOOL
            )
            plugin = MockPlugin(manifest, {})
            registry.register_plugin(f"plugin-{i}", plugin, manifest)

        plugins = registry.list_plugins()
        assert len(plugins) == 3

    def test_list_plugins_by_type(self, registry):
        """Test listing plugins by type"""

        # Register different types
        for plugin_type in [PluginType.TOOL, PluginType.REASONING, PluginType.TOOL]:
            manifest = PluginManifest(
                id=f"plugin-{plugin_type.value}",
                name=f"Plugin {plugin_type.value}",
                version="1.0.0",
                description="Test",
                type=plugin_type
            )
            plugin = MockPlugin(manifest, {})
            registry.register_plugin(manifest.id, plugin, manifest)

        tool_plugins = registry.list_plugins(plugin_type=PluginType.TOOL)
        assert len(tool_plugins) == 2

        reasoning_plugins = registry.list_plugins(plugin_type=PluginType.REASONING)
        assert len(reasoning_plugins) == 1

    @pytest.mark.asyncio
    async def test_activate_plugin(self, registry):
        """Test activating plugin"""

        manifest = PluginManifest(
            id="activate-test",
            name="Activate Test",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        plugin = MockPlugin(manifest, {})
        registry.register_plugin("activate-test", plugin, manifest)

        success = await registry.activate_plugin("activate-test")

        assert success == True
        assert plugin.initialized == True

    @pytest.mark.asyncio
    async def test_deactivate_plugin(self, registry):
        """Test deactivating plugin"""

        manifest = PluginManifest(
            id="deactivate-test",
            name="Deactivate Test",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        plugin = MockPlugin(manifest, {})
        registry.register_plugin("deactivate-test", plugin, manifest)

        await registry.activate_plugin("deactivate-test")
        assert plugin.initialized == True

        await registry.deactivate_plugin("deactivate-test")
        assert plugin.initialized == False

    @pytest.mark.asyncio
    async def test_unload_plugin(self, registry):
        """Test unloading plugin"""

        manifest = PluginManifest(
            id="unload-test",
            name="Unload Test",
            version="1.0.0",
            description="Test",
            type=PluginType.TOOL
        )

        plugin = MockPlugin(manifest, {})
        registry.register_plugin("unload-test", plugin, manifest)

        await registry.unload_plugin("unload-test")

        assert registry.get_plugin("unload-test") is None


class TestIntegration:
    """Integration tests for plugin system"""

    @pytest.mark.asyncio
    async def test_full_plugin_lifecycle(self, tmp_path):
        """Test complete plugin lifecycle"""

        registry = PluginRegistry(tmp_path)

        # 1. Create manifest
        manifest = PluginManifest(
            id="lifecycle-test",
            name="Lifecycle Test",
            version="1.0.0",
            description="Full lifecycle test",
            type=PluginType.TOOL,
            capabilities=["test"],
            permissions=["network:test.com"]
        )

        # 2. Create plugin
        plugin = MockPlugin(manifest, {"key": "value"})

        # 3. Register
        registry.register_plugin("lifecycle-test", plugin, manifest)
        assert registry.get_plugin("lifecycle-test") == plugin

        # 4. Activate
        success = await registry.activate_plugin("lifecycle-test")
        assert success == True
        assert plugin.initialized == True

        # 5. Use plugin
        result = await plugin.test_method("test")
        assert result == "processed: test"

        # 6. Deactivate
        await registry.deactivate_plugin("lifecycle-test")
        assert plugin.initialized == False

        # 7. Unload
        await registry.unload_plugin("lifecycle-test")
        assert registry.get_plugin("lifecycle-test") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
