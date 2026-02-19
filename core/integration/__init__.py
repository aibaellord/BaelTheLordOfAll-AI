"""
🔮 BAEL INTEGRATION MODULE
===========================
The Central Nervous System of BAEL

This module provides:
- UnifiedHub: Single access to ALL 500+ BAEL modules
- MasterPowerInterface: Ultimate unified API
- MasterIntegrationLayer: Core integration layer
- Cross-module orchestration
- Intelligent routing

Usage:
    from core.integration import get_master, get_hub

    # Quick access to full power
    bael = await get_master()
    result = await bael.chat("Build me a web app")
"""

# Legacy imports
from .master_integration import (
    EventBus, IntegrationConfig, IntegrationMode,
    MasterIntegrationLayer, OperationContext,
    OperationResult, SystemHealth, SystemRegistry,
    SystemState, create_bael
)

# New unified systems
try:
    from .unified_hub import (
        UnifiedHub, SystemDomain, CapabilityLevel,
        SystemModule, HubRequest, HubResponse,
        ModuleRegistry, CapabilityRouter,
        create_unified_hub, get_hub
    )
except ImportError:
    UnifiedHub = None
    get_hub = None

try:
    from .master_power_interface import (
        MasterPowerInterface, PowerLevel, OperationMode as PowerMode,
        PowerRequest, PowerResponse, IntentAnalyzer, PowerRouter,
        create_master_power, get_bael, get_master
    )
except ImportError:
    MasterPowerInterface = None
    get_master = None


__all__ = [
    # Legacy
    "MasterIntegrationLayer",
    "IntegrationConfig",
    "IntegrationMode",
    "SystemState",
    "SystemHealth",
    "OperationContext",
    "OperationResult",
    "SystemRegistry",
    "EventBus",
    "create_bael",

    # New - UnifiedHub
    "UnifiedHub",
    "SystemDomain",
    "CapabilityLevel",
    "SystemModule",
    "HubRequest",
    "HubResponse",
    "ModuleRegistry",
    "CapabilityRouter",
    "create_unified_hub",
    "get_hub",

    # New - MasterPowerInterface
    "MasterPowerInterface",
    "PowerLevel",
    "PowerMode",
    "PowerRequest",
    "PowerResponse",
    "IntentAnalyzer",
    "PowerRouter",
    "create_master_power",
    "get_bael",
    "get_master",
]

__version__ = "2.0.0"
