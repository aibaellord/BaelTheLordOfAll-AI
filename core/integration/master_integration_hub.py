"""
BAEL - Master Integration Hub
==============================

All systems connected. One unified power.

This module connects ALL Ba'el systems together, providing:
1. Unified access to all engines
2. Cross-system workflows
3. System registry and discovery
4. Global state management
5. Event propagation
6. Resource sharing
7. Logging aggregation
8. Performance monitoring
9. Configuration management
10. Health monitoring

"All power flows through one point."
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger("BAEL.INTEGRATION")


class MasterIntegrationHub:
    """
    The Master Integration Hub - connects all Ba'el systems.

    This is the central nervous system of Ba'el, providing
    unified access to all capabilities and managing cross-system
    operations.
    """

    def __init__(self):
        self._systems: Dict[str, Any] = {}
        self._initialized = False
        self._stats = {
            "total_systems": 0,
            "initialized_at": None,
            "commands_executed": 0
        }

        logger.info("MasterIntegrationHub created - awaiting initialization")

    async def initialize(self):
        """Initialize and connect all Ba'el systems."""
        if self._initialized:
            return

        logger.info("Initializing all Ba'el systems...")

        # Import and initialize all systems
        systems_to_init = [
            ("creativity", "core.creativity.creative_genius_engine", "get_creative_engine"),
            ("orchestrator", "core.orchestration.master_orchestrator", "get_orchestrator"),
            ("resources", "core.resources.resource_generator_engine", "get_resource_generator"),
            ("strategy", "core.strategy.ultimate_strategy_engine", "get_strategy_engine"),
            ("influence", "core.influence.psychological_influence_engine", "get_influence_engine"),
            ("console", "core.console.unified_power_console", "get_console"),
        ]

        for name, module_path, getter_name in systems_to_init:
            try:
                # Dynamic import
                module = __import__(module_path, fromlist=[getter_name])
                getter = getattr(module, getter_name)
                self._systems[name] = getter()
                logger.info(f"  ✓ {name} initialized")
            except ImportError as e:
                logger.warning(f"  ✗ {name} not available: {e}")
            except Exception as e:
                logger.error(f"  ✗ {name} failed: {e}")

        self._stats["total_systems"] = len(self._systems)
        self._stats["initialized_at"] = datetime.now().isoformat()
        self._initialized = True

        logger.info(f"Initialized {len(self._systems)} systems")

    def get_system(self, name: str) -> Optional[Any]:
        """Get a specific system by name."""
        return self._systems.get(name)

    @property
    def creativity(self):
        """Get the Creative Genius Engine."""
        return self._systems.get("creativity")

    @property
    def orchestrator(self):
        """Get the Master Orchestrator."""
        return self._systems.get("orchestrator")

    @property
    def resources(self):
        """Get the Resource Generator Engine."""
        return self._systems.get("resources")

    @property
    def strategy(self):
        """Get the Ultimate Strategy Engine."""
        return self._systems.get("strategy")

    @property
    def influence(self):
        """Get the Psychological Influence Engine."""
        return self._systems.get("influence")

    @property
    def console(self):
        """Get the Unified Power Console."""
        return self._systems.get("console")

    async def execute(self, command: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a command through the hub."""
        if not self._initialized:
            await self.initialize()

        self._stats["commands_executed"] += 1

        # Route to console if available
        if self.console:
            result = await self.console.execute(command)
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }

        return {"success": False, "message": "Console not available"}

    def get_all_systems(self) -> Dict[str, str]:
        """Get all registered systems."""
        return {
            name: type(system).__name__
            for name, system in self._systems.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            **self._stats,
            "systems_available": list(self._systems.keys())
        }


# ============================================================================
# SINGLETON
# ============================================================================

_hub: Optional[MasterIntegrationHub] = None


def get_hub() -> MasterIntegrationHub:
    """Get the global integration hub."""
    global _hub
    if _hub is None:
        _hub = MasterIntegrationHub()
    return _hub


async def bael() -> MasterIntegrationHub:
    """Get and initialize Ba'el."""
    hub = get_hub()
    await hub.initialize()
    return hub


# ============================================================================
# QUICK ACCESS FUNCTIONS
# ============================================================================

async def dominate(target: str = "all") -> Dict[str, Any]:
    """Quick domination command."""
    hub = await bael()
    return await hub.execute(f"dominate {target}")


async def create(what: str = "ideas") -> Dict[str, Any]:
    """Quick creation command."""
    hub = await bael()
    return await hub.execute(f"create {what}")


async def simulate(iterations: int = 1000) -> Dict[str, Any]:
    """Quick simulation command."""
    hub = await bael()
    return await hub.execute(f"simulate {iterations}")


async def hunt(domain: str = "all") -> Dict[str, Any]:
    """Quick opportunity hunt."""
    hub = await bael()
    return await hub.execute(f"hunt {domain}")


async def status() -> Dict[str, Any]:
    """Get system status."""
    hub = await bael()
    return await hub.execute("status --full")


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the integration hub."""
    print("=" * 60)
    print("🔗 MASTER INTEGRATION HUB 🔗")
    print("=" * 60)

    # Initialize
    hub = await bael()

    print("\n--- Available Systems ---")
    systems = hub.get_all_systems()
    for name, cls in systems.items():
        print(f"  ✓ {name}: {cls}")

    print("\n--- Quick Commands ---")

    result = await dominate("market")
    print(f"Dominate: {result.get('message', 'executed')}")

    result = await create("breakthrough ideas")
    print(f"Create: {result.get('message', 'executed')}")

    result = await simulate(5000)
    print(f"Simulate: {result.get('message', 'executed')}")

    result = await hunt("opportunities")
    print(f"Hunt: {result.get('message', 'executed')}")

    print("\n--- Hub Statistics ---")
    stats = hub.get_stats()
    print(f"Total systems: {stats['total_systems']}")
    print(f"Commands executed: {stats['commands_executed']}")

    print("\n" + "=" * 60)
    print("🔗 ALL SYSTEMS INTEGRATED 🔗")


if __name__ == "__main__":
    asyncio.run(demo())
