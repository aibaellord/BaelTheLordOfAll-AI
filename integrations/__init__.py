"""
BAEL - Integration Providers
Connectors for external services and platforms.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Integrations")


class IntegrationStatus(Enum):
    """Status of an integration."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    CONFIGURING = "configuring"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    name: str
    type: str
    enabled: bool
    credentials: Dict[str, str]
    settings: Dict[str, Any]


class BaseIntegration:
    """Base class for all integrations."""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.DISCONNECTED
        self._client = None

    async def connect(self) -> bool:
        """Connect to the service."""
        raise NotImplementedError

    async def disconnect(self) -> None:
        """Disconnect from the service."""
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """Test the connection."""
        raise NotImplementedError

    async def health_check(self) -> Dict[str, Any]:
        """Check integration health."""
        return {
            "name": self.config.name,
            "status": self.status.value,
            "enabled": self.config.enabled
        }


class IntegrationRegistry:
    """Registry for managing integrations."""

    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._providers: Dict[str, type] = {}

    def register_provider(self, name: str, provider_class: type) -> None:
        """Register an integration provider."""
        self._providers[name] = provider_class
        logger.info(f"Registered integration provider: {name}")

    def create_integration(self, config: IntegrationConfig) -> Optional[BaseIntegration]:
        """Create an integration from config."""
        provider_class = self._providers.get(config.type)
        if not provider_class:
            logger.warning(f"Unknown integration type: {config.type}")
            return None

        integration = provider_class(config)
        self._integrations[config.name] = integration
        return integration

    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """Get an integration by name."""
        return self._integrations.get(name)

    def list_integrations(self) -> List[str]:
        """List all registered integrations."""
        return list(self._integrations.keys())

    def list_providers(self) -> List[str]:
        """List available providers."""
        return list(self._providers.keys())

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all enabled integrations."""
        results = {}
        for name, integration in self._integrations.items():
            if integration.config.enabled:
                try:
                    results[name] = await integration.connect()
                except Exception as e:
                    logger.error(f"Failed to connect {name}: {e}")
                    results[name] = False
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all integrations."""
        for integration in self._integrations.values():
            try:
                await integration.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {integration.config.name}: {e}")

    async def health_check_all(self) -> Dict[str, Any]:
        """Check health of all integrations."""
        return {
            name: await integration.health_check()
            for name, integration in self._integrations.items()
        }


# Global registry
registry = IntegrationRegistry()

__all__ = [
    "IntegrationStatus",
    "IntegrationConfig",
    "BaseIntegration",
    "IntegrationRegistry",
    "registry"
]
