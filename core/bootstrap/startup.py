"""
BAEL Startup Orchestrator
===========================
The single entrypoint for full BAEL system initialization.

Call `await BAELStartup.initialize()` to bring up everything:
1. Universal Auto-Loader (discovers all capabilities)
2. Reference Loader (bridges .agent, .ai, .gemini)
3. Master Registry (registers everything)
4. Core Orchestrators (supreme, apex, ultimate, etc.)
5. MCP Server (exposes tools to Claude/VSCode)
6. API Health (ensures API is ready)

Provides startup lifecycle hooks for custom initialization logic.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .auto_loader import UniversalAutoLoader, get_auto_loader, load_all_capabilities
from .reference_loader import ReferenceLoader
from .registry import MasterRegistry, get_registry

logger = logging.getLogger("BAEL.Bootstrap.Startup")

PROJECT_ROOT = Path(__file__).parent.parent.parent


class StartupPhase(Enum):
    PENDING = "pending"
    AUTO_LOADING = "auto_loading"
    REFERENCE_LOADING = "reference_loading"
    REGISTRY_INIT = "registry_init"
    ORCHESTRATOR_INIT = "orchestrator_init"
    MCP_INIT = "mcp_init"
    API_READY = "api_ready"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class StartupResult:
    success: bool
    phase_reached: StartupPhase
    duration_ms: float
    capabilities_loaded: int = 0
    agents_registered: int = 0
    plugins_loaded: int = 0
    workflows_registered: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "phase": self.phase_reached.value,
            "duration_ms": round(self.duration_ms, 2),
            "capabilities_loaded": self.capabilities_loaded,
            "agents_registered": self.agents_registered,
            "plugins_loaded": self.plugins_loaded,
            "workflows_registered": self.workflows_registered,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StartupConfig:
    """Configuration for BAEL startup."""
    enable_auto_loader: bool = True
    enable_reference_loader: bool = True
    enable_core_orchestrators: bool = True
    enable_mcp: bool = False  # MCP server is started separately
    log_level: str = "INFO"
    max_startup_seconds: float = 120.0
    fail_fast: bool = False  # If True, any error stops startup


class BAELStartup:
    """
    Full BAEL system startup orchestrator.

    Usage:
        startup = BAELStartup()
        result = await startup.initialize()
        print(f"Startup {'OK' if result.success else 'FAILED'}")
        print(f"  {result.capabilities_loaded} capabilities loaded")
    """

    _instance: Optional["BAELStartup"] = None

    def __new__(cls, config: Optional[StartupConfig] = None) -> "BAELStartup":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[StartupConfig] = None):
        if self._initialized:
            return
        self.config = config or StartupConfig()
        self.phase = StartupPhase.PENDING
        self.result: Optional[StartupResult] = None
        self._hooks: Dict[StartupPhase, List[Callable]] = {
            phase: [] for phase in StartupPhase
        }
        self.registry = get_registry()
        self.auto_loader = get_auto_loader()
        self.reference_loader = ReferenceLoader()
        self._initialized = True

    def add_hook(self, phase: StartupPhase, hook: Callable) -> None:
        """Add a startup phase hook. Called when the given phase starts."""
        self._hooks[phase].append(hook)

    async def _run_hooks(self, phase: StartupPhase, context: Dict[str, Any]) -> None:
        for hook in self._hooks.get(phase, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.warning(f"Startup hook error at {phase.value}: {e}")

    async def initialize(self) -> StartupResult:
        """Run the full BAEL startup sequence."""
        start_time = time.monotonic()
        errors: List[str] = []
        warnings: List[str] = []
        capabilities_loaded = 0
        agents_registered = 0
        plugins_loaded = 0
        workflows_registered = 0

        self._print_banner()

        try:
            # ----------------------------------------------------------------
            # PHASE 1: AUTO-LOADING
            # ----------------------------------------------------------------
            self.phase = StartupPhase.AUTO_LOADING
            await self._run_hooks(self.phase, {})

            if self.config.enable_auto_loader:
                logger.info("\n📡 Phase 1: Universal Auto-Loader")
                try:
                    caps = await asyncio.wait_for(
                        self.auto_loader.load_all(),
                        timeout=self.config.max_startup_seconds / 4
                    )
                    capabilities_loaded = len(caps)

                    # Register all capabilities in master registry
                    for cap_id, cap in caps.items():
                        if cap.enabled and not cap.error:
                            self.registry.register(
                                item_id=cap.id,
                                name=cap.name,
                                item_type=cap.type.value,
                                metadata=cap.metadata,
                                handler=cap.module,
                                tags={cap.type.value, "auto_loaded"},
                            )

                    plugins_loaded = len([c for c in caps.values() if c.type.value == "plugin"])
                    workflows_registered = len([c for c in caps.values() if c.type.value == "workflow"])

                    logger.info(f"   ✅ {capabilities_loaded} capabilities discovered & registered")
                except asyncio.TimeoutError:
                    warnings.append("Auto-loader timed out; partial capabilities loaded")
                    logger.warning("   ⚠️  Auto-loader timed out")
                except Exception as e:
                    error_msg = f"Auto-loader failed: {e}"
                    errors.append(error_msg)
                    logger.error(f"   ❌ {error_msg}")
                    if self.config.fail_fast:
                        raise

            # ----------------------------------------------------------------
            # PHASE 2: REFERENCE LOADING
            # ----------------------------------------------------------------
            self.phase = StartupPhase.REFERENCE_LOADING
            await self._run_hooks(self.phase, {})

            if self.config.enable_reference_loader:
                logger.info("\n🔗 Phase 2: Reference Folder Loader")
                try:
                    ref_result = await asyncio.wait_for(
                        self.reference_loader.load_all(),
                        timeout=30.0
                    )
                    agents_registered = ref_result.get("agents", 0)
                    logger.info(f"   ✅ {ref_result.get('total', 0)} reference items loaded")
                except asyncio.TimeoutError:
                    warnings.append("Reference loader timed out")
                    logger.warning("   ⚠️  Reference loader timed out")
                except Exception as e:
                    error_msg = f"Reference loader failed: {e}"
                    errors.append(error_msg)
                    logger.error(f"   ❌ {error_msg}")
                    if self.config.fail_fast:
                        raise

            # ----------------------------------------------------------------
            # PHASE 3: REGISTRY SUMMARY
            # ----------------------------------------------------------------
            self.phase = StartupPhase.REGISTRY_INIT
            await self._run_hooks(self.phase, {})

            stats = self.registry.stats()
            logger.info(f"\n📊 Phase 3: Master Registry")
            logger.info(f"   Total registered: {sum(stats.values())}")
            for item_type, count in sorted(stats.items(), key=lambda x: -x[1]):
                logger.info(f"   {item_type:30s}: {count}")

            # ----------------------------------------------------------------
            # PHASE 4: CORE ORCHESTRATORS
            # ----------------------------------------------------------------
            self.phase = StartupPhase.ORCHESTRATOR_INIT
            await self._run_hooks(self.phase, {})

            if self.config.enable_core_orchestrators:
                logger.info("\n⚡ Phase 4: Core Orchestrators")
                await self._init_core_orchestrators(errors, warnings)

            # ----------------------------------------------------------------
            # COMPLETE
            # ----------------------------------------------------------------
            self.phase = StartupPhase.COMPLETE
            await self._run_hooks(self.phase, {})

            duration_ms = (time.monotonic() - start_time) * 1000
            self.result = StartupResult(
                success=len(errors) == 0,
                phase_reached=self.phase,
                duration_ms=duration_ms,
                capabilities_loaded=capabilities_loaded,
                agents_registered=agents_registered,
                plugins_loaded=plugins_loaded,
                workflows_registered=workflows_registered,
                errors=errors,
                warnings=warnings,
            )

            self._print_completion(self.result)
            return self.result

        except Exception as e:
            self.phase = StartupPhase.FAILED
            duration_ms = (time.monotonic() - start_time) * 1000
            errors.append(f"Fatal startup error: {str(e)}")
            logger.critical(f"🚨 BAEL startup FAILED: {e}", exc_info=True)

            self.result = StartupResult(
                success=False,
                phase_reached=self.phase,
                duration_ms=duration_ms,
                errors=errors,
                warnings=warnings,
            )
            return self.result

    async def _init_core_orchestrators(
        self, errors: List[str], warnings: List[str]
    ) -> None:
        """Initialize core orchestrators (best-effort)."""
        orchestrators_to_try = [
            ("Supreme Controller", "core.supreme.orchestrator", "SupremeController"),
            ("Ultimate Orchestrator", "core.ultimate.ultimate_orchestrator", "UltimateOrchestrator"),
            ("APEX Orchestrator", "core.apex.apex_orchestrator", "APEXOrchestrator"),
            ("Lord of All", "core.lord_of_all.lord_of_all_orchestrator", "LordOfAllOrchestrator"),
        ]

        for name, module_path, class_name in orchestrators_to_try:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name, None)
                if cls:
                    self.registry.register(
                        item_id=f"orchestrator.{class_name.lower()}",
                        name=name,
                        item_type="orchestrator",
                        handler=cls,
                        tags={"orchestrator", "core"},
                        description=f"Core BAEL orchestrator: {name}",
                    )
                    logger.info(f"   ✅ {name}")
                else:
                    warnings.append(f"Class {class_name} not found in {module_path}")
            except ImportError as e:
                logger.debug(f"   ⚠️  {name}: not available ({e})")
            except Exception as e:
                warnings.append(f"{name} init error: {e}")
                logger.warning(f"   ⚠️  {name} error: {e}")

    def _print_banner(self) -> None:
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║          🔥 BAEL - The Lord of All AI Agents 🔥              ║")
        logger.info("║                 System Startup Sequence                      ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")
        logger.info("")

    def _print_completion(self, result: StartupResult) -> None:
        status = "✅ SUCCESS" if result.success else "⚠️  PARTIAL"
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info(f"║  {status:<60}║")
        logger.info(f"║  Startup time: {result.duration_ms:.0f}ms{'':<45}║")
        logger.info(f"║  Capabilities: {result.capabilities_loaded:<46}║")
        logger.info(f"║  Plugins:      {result.plugins_loaded:<46}║")
        logger.info(f"║  Workflows:    {result.workflows_registered:<46}║")
        if result.errors:
            logger.info(f"║  ❌ Errors:    {len(result.errors):<46}║")
        if result.warnings:
            logger.info(f"║  ⚠️  Warnings:  {len(result.warnings):<46}║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")
        logger.info("")

    def is_ready(self) -> bool:
        return self.phase == StartupPhase.COMPLETE

    def get_status(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "ready": self.is_ready(),
            "result": self.result.to_dict() if self.result else None,
            "registry_stats": self.registry.stats(),
        }


# =============================================================================
# CONVENIENCE API
# =============================================================================

_startup: Optional[BAELStartup] = None


async def initialize(
    config: Optional[StartupConfig] = None,
    *,
    fail_fast: bool = False,
) -> StartupResult:
    """Initialize the full BAEL system. Returns startup result."""
    global _startup
    if config is None:
        config = StartupConfig(fail_fast=fail_fast)
    _startup = BAELStartup(config)
    return await _startup.initialize()


def get_startup() -> Optional[BAELStartup]:
    return _startup


def is_ready() -> bool:
    return _startup is not None and _startup.is_ready()
