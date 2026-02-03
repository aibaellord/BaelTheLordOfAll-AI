"""
BAEL - Capability Manager
Manages dynamic capability loading and expansion.
"""

import asyncio
import importlib
import importlib.util
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from . import CapabilityDefinition

logger = logging.getLogger("BAEL.Evolution.Capabilities")


@dataclass
class LoadedCapability:
    """A loaded capability instance."""
    definition: CapabilityDefinition
    module: Any
    instance: Optional[Any]
    loaded_at: float
    active: bool = True


class CapabilityManager:
    """
    Manages dynamic capability loading and expansion.

    Features:
    - Dynamic module loading
    - Capability registration
    - Version management
    - Dependency resolution
    - Hot reloading
    """

    def __init__(self, capability_dir: Optional[str] = None):
        self._capability_dir = Path(capability_dir or "core")
        self._registry: Dict[str, CapabilityDefinition] = {}
        self._loaded: Dict[str, LoadedCapability] = {}
        self._hooks: Dict[str, List[Callable]] = {}

        # Discover existing capabilities
        self._discover_capabilities()

    def _discover_capabilities(self) -> None:
        """Discover capabilities from the filesystem."""
        if not self._capability_dir.exists():
            return

        for path in self._capability_dir.iterdir():
            if path.is_dir() and (path / "__init__.py").exists():
                try:
                    self._register_from_path(path)
                except Exception as e:
                    logger.debug(f"Failed to discover capability at {path}: {e}")

    def _register_from_path(self, path: Path) -> None:
        """Register a capability from a directory path."""
        init_file = path / "__init__.py"

        # Read init file for metadata
        content = init_file.read_text()

        # Extract docstring as description
        description = ""
        if '"""' in content:
            start = content.find('"""') + 3
            end = content.find('"""', start)
            if end > start:
                description = content[start:end].strip()

        # Create definition
        definition = CapabilityDefinition(
            id=path.name,
            name=path.name.replace("_", " ").title(),
            description=description or f"Capability: {path.name}",
            module_path=str(path),
            entry_point=f"core.{path.name}",
            dependencies=[],
            version="1.0.0"
        )

        self._registry[definition.id] = definition

    def register(self, definition: CapabilityDefinition) -> bool:
        """
        Register a new capability.

        Args:
            definition: Capability definition

        Returns:
            Success status
        """
        if definition.id in self._registry:
            logger.warning(f"Capability {definition.id} already registered")
            return False

        self._registry[definition.id] = definition
        logger.info(f"Registered capability: {definition.name}")
        return True

    def unregister(self, capability_id: str) -> bool:
        """
        Unregister a capability.

        Args:
            capability_id: Capability ID

        Returns:
            Success status
        """
        if capability_id in self._loaded:
            self.unload(capability_id)

        if capability_id in self._registry:
            del self._registry[capability_id]
            return True

        return False

    async def load(
        self,
        capability_id: str,
        force: bool = False
    ) -> Optional[LoadedCapability]:
        """
        Load a capability.

        Args:
            capability_id: Capability ID
            force: Force reload if already loaded

        Returns:
            Loaded capability or None
        """
        # Check if already loaded
        if capability_id in self._loaded and not force:
            return self._loaded[capability_id]

        # Get definition
        definition = self._registry.get(capability_id)
        if not definition:
            logger.error(f"Capability {capability_id} not found")
            return None

        # Resolve dependencies
        for dep_id in definition.dependencies:
            if dep_id not in self._loaded:
                dep_loaded = await self.load(dep_id)
                if not dep_loaded:
                    logger.error(f"Failed to load dependency: {dep_id}")
                    return None

        try:
            # Import module
            module = importlib.import_module(definition.entry_point)

            # Create instance if possible
            instance = None
            if hasattr(module, "create_instance"):
                instance = await module.create_instance()
            elif hasattr(module, "get_instance"):
                instance = module.get_instance()

            loaded = LoadedCapability(
                definition=definition,
                module=module,
                instance=instance,
                loaded_at=time.time()
            )

            self._loaded[capability_id] = loaded

            # Trigger hooks
            await self._trigger_hooks("on_load", capability_id, loaded)

            logger.info(f"Loaded capability: {definition.name}")
            return loaded

        except Exception as e:
            logger.error(f"Failed to load capability {capability_id}: {e}")
            return None

    def unload(self, capability_id: str) -> bool:
        """
        Unload a capability.

        Args:
            capability_id: Capability ID

        Returns:
            Success status
        """
        if capability_id not in self._loaded:
            return False

        loaded = self._loaded[capability_id]

        try:
            # Cleanup if available
            if loaded.instance and hasattr(loaded.instance, "cleanup"):
                loaded.instance.cleanup()

            # Remove from sys.modules for clean reload
            module_name = loaded.definition.entry_point
            if module_name in sys.modules:
                del sys.modules[module_name]

            del self._loaded[capability_id]

            logger.info(f"Unloaded capability: {loaded.definition.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload capability {capability_id}: {e}")
            return False

    async def reload(self, capability_id: str) -> Optional[LoadedCapability]:
        """
        Reload a capability.

        Args:
            capability_id: Capability ID

        Returns:
            Reloaded capability or None
        """
        self.unload(capability_id)
        return await self.load(capability_id, force=True)

    def get(self, capability_id: str) -> Optional[Any]:
        """
        Get a loaded capability's instance.

        Args:
            capability_id: Capability ID

        Returns:
            Capability instance or None
        """
        loaded = self._loaded.get(capability_id)
        if loaded:
            return loaded.instance or loaded.module
        return None

    def is_loaded(self, capability_id: str) -> bool:
        """Check if a capability is loaded."""
        return capability_id in self._loaded

    def list_registered(self) -> List[CapabilityDefinition]:
        """List all registered capabilities."""
        return list(self._registry.values())

    def list_loaded(self) -> List[LoadedCapability]:
        """List all loaded capabilities."""
        return list(self._loaded.values())

    async def load_all(self) -> Dict[str, bool]:
        """
        Load all registered capabilities.

        Returns:
            Dict of capability_id -> success
        """
        results = {}

        for capability_id in self._registry:
            loaded = await self.load(capability_id)
            results[capability_id] = loaded is not None

        return results

    def add_hook(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """
        Add a hook for capability events.

        Args:
            event: Event name (on_load, on_unload)
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    async def _trigger_hooks(
        self,
        event: str,
        capability_id: str,
        loaded: LoadedCapability
    ) -> None:
        """Trigger hooks for an event."""
        for callback in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(capability_id, loaded)
                else:
                    callback(capability_id, loaded)
            except Exception as e:
                logger.warning(f"Hook error for {event}: {e}")

    async def create_capability(
        self,
        name: str,
        description: str,
        code: str
    ) -> Optional[CapabilityDefinition]:
        """
        Create a new capability from code.

        Args:
            name: Capability name
            description: Description
            code: Python code

        Returns:
            Created capability definition or None
        """
        capability_id = name.lower().replace(" ", "_")
        capability_path = self._capability_dir / capability_id

        try:
            # Create directory
            capability_path.mkdir(parents=True, exist_ok=True)

            # Create __init__.py
            init_content = f'''"""
{description}
"""

{code}
'''
            (capability_path / "__init__.py").write_text(init_content)

            # Create definition
            definition = CapabilityDefinition(
                id=capability_id,
                name=name,
                description=description,
                module_path=str(capability_path),
                entry_point=f"core.{capability_id}",
                dependencies=[],
                version="1.0.0"
            )

            self.register(definition)

            logger.info(f"Created new capability: {name}")
            return definition

        except Exception as e:
            logger.error(f"Failed to create capability: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get capability manager status."""
        return {
            "registered": len(self._registry),
            "loaded": len(self._loaded),
            "capabilities": {
                cap_id: {
                    "name": cap.name,
                    "loaded": cap_id in self._loaded,
                    "version": cap.version
                }
                for cap_id, cap in self._registry.items()
            }
        }

    def export_manifest(self) -> Dict[str, Any]:
        """Export capability manifest."""
        return {
            "capabilities": [
                {
                    "id": cap.id,
                    "name": cap.name,
                    "description": cap.description,
                    "entry_point": cap.entry_point,
                    "dependencies": cap.dependencies,
                    "version": cap.version
                }
                for cap in self._registry.values()
            ],
            "exported_at": time.time()
        }

    def import_manifest(self, manifest: Dict[str, Any]) -> int:
        """
        Import capabilities from manifest.

        Returns:
            Number of capabilities imported
        """
        count = 0

        for cap_data in manifest.get("capabilities", []):
            try:
                definition = CapabilityDefinition(
                    id=cap_data["id"],
                    name=cap_data["name"],
                    description=cap_data.get("description", ""),
                    module_path=cap_data.get("module_path", ""),
                    entry_point=cap_data["entry_point"],
                    dependencies=cap_data.get("dependencies", []),
                    version=cap_data.get("version", "1.0.0")
                )

                if self.register(definition):
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to import capability: {e}")

        return count


# Global instance
_capability_manager: Optional[CapabilityManager] = None


def get_capability_manager(
    capability_dir: Optional[str] = None
) -> CapabilityManager:
    """Get or create capability manager instance."""
    global _capability_manager
    if _capability_manager is None:
        _capability_manager = CapabilityManager(capability_dir)
    return _capability_manager
