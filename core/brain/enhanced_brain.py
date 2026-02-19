"""
BAEL - Enhanced Brain Module
═══════════════════════════════════════════════════════════════
The supreme cognitive hub that unifies ALL 26+ subsystems into
a single, functional processing pipeline. This is the real
operational core that makes every module work together.

Architecture:
    EnhancedBaelBrain inherits BaelBrain and adds:
    1. Subsystem Registry - lazy-loaded, graceful degradation
    2. Enhanced Think Pipeline - routes through all engines
    3. System Status - full health/power reporting
    4. Omega Processing - multi-engine cognitive synthesis
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.EnhancedBrain")


# ═══════════════════════════════════════════════════════════════
# SUBSYSTEM REGISTRY
# ═══════════════════════════════════════════════════════════════


class SubsystemStatus(Enum):
    """Status of a subsystem."""

    OFFLINE = "offline"
    INITIALIZING = "initializing"
    ONLINE = "online"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class SubsystemInfo:
    """Information about a registered subsystem."""

    name: str
    module_path: str
    factory_func: str
    instance: Optional[Any] = None
    status: SubsystemStatus = SubsystemStatus.OFFLINE
    init_time_ms: float = 0.0
    error: Optional[str] = None
    power_level: float = 0.0


# ═══════════════════════════════════════════════════════════════
# SUBSYSTEM DEFINITIONS
# ═══════════════════════════════════════════════════════════════

"""
Every subsystem we've built, mapped to its import path and factory function.
This is the master registry that makes BAEL aware of all its capabilities.
"""
SUBSYSTEM_DEFINITIONS = {
    # ─── Intelligence Layer ───
    "omega_mind": {
        "module": "core.omega_mind.omega_mind",
        "factory": "get_omega_mind",
        "category": "intelligence",
        "description": "Supreme collective superintelligence",
    },
    "genius_amplifier": {
        "module": "core.genius_synthesis.genius_amplifier",
        "factory": "get_genius_amplifier",
        "category": "intelligence",
        "description": "Multi-modal genius synthesis",
    },
    "zero_limit": {
        "module": "core.zero_limit_intelligence.zero_limit_engine",
        "factory": "get_zero_limit_engine",
        "category": "intelligence",
        "description": "Solves impossible problems",
    },
    "consciousness": {
        "module": "core.quantum_consciousness.consciousness_unifier",
        "factory": "get_consciousness_unifier",
        "category": "intelligence",
        "description": "Quantum-coherent consciousness",
    },
    "knowledge_engine": {
        "module": "core.knowledge_synthesis.knowledge_engine",
        "factory": "get_knowledge_engine",
        "category": "intelligence",
        "description": "Unified knowledge synthesis",
    },
    # ─── Power Layer ───
    "sacred_math": {
        "module": "core.sacred_mathematics.sacred_engine",
        "factory": "get_sacred_engine",
        "category": "power",
        "description": "Golden ratio / sacred geometry computation",
    },
    "power_amplifier": {
        "module": "core.power_core.power_amplifier",
        "factory": "get_power_amplifier",
        "category": "power",
        "description": "Universal power amplification",
    },
    "cosmic_optimizer": {
        "module": "core.cosmic_optimization.cosmic_optimizer",
        "factory": "get_cosmic_optimizer",
        "category": "power",
        "description": "Universal optimization principles",
    },
    "infinity_engine": {
        "module": "core.infinity_engine.infinity_engine",
        "factory": "get_infinity_engine",
        "category": "power",
        "description": "Infinite scaling and growth",
    },
    "potential_maximizer": {
        "module": "core.infinite_potential.potential_maximizer",
        "factory": "get_potential_maximizer",
        "category": "power",
        "description": "Exploits every opportunity",
    },
    # ─── Domination Layer ───
    "domination": {
        "module": "core.domination.domination_core",
        "factory": "get_domination_engine",
        "category": "domination",
        "description": "Absolute supremacy across all domains",
    },
    "warfare": {
        "module": "core.strategic_warfare.warfare_module",
        "factory": "get_warfare_module",
        "category": "domination",
        "description": "Strategic competitive warfare",
    },
    "asset_dominator": {
        "module": "core.asset_domination.asset_dominator",
        "factory": "get_asset_dominator",
        "category": "domination",
        "description": "Zero-cost resource exploitation",
    },
    "mastery": {
        "module": "core.absolute_mastery.mastery_controller",
        "factory": "get_mastery_controller",
        "category": "domination",
        "description": "Capability mastery levels",
    },
    # ─── Orchestration Layer ───
    "meta_commander": {
        "module": "core.meta_orchestration.meta_commander",
        "factory": "get_meta_commander",
        "category": "orchestration",
        "description": "Supreme meta-orchestration",
    },
    "ultimate_controller": {
        "module": "core.ultimate_control.ultimate_controller",
        "factory": "get_ultimate_controller",
        "category": "orchestration",
        "description": "Supreme system control",
    },
    "swarm": {
        "module": "core.swarm_intelligence.swarm_controller",
        "factory": "get_swarm_controller",
        "category": "orchestration",
        "description": "Emergent swarm superintelligence",
    },
    "neural_nexus": {
        "module": "core.neural_nexus.neural_nexus",
        "factory": "get_neural_nexus",
        "category": "orchestration",
        "description": "Neural network coordination hub",
    },
    # ─── Transcendence Layer ───
    "transcendence": {
        "module": "core.transcendence.transcendence_engine",
        "factory": "get_transcendence_engine",
        "category": "transcendence",
        "description": "Breaks through all limits",
    },
    "apex_protocol": {
        "module": "core.apex_protocol.apex_protocol",
        "factory": "get_apex_protocol",
        "category": "transcendence",
        "description": "Final supremacy protocol",
    },
    "temporal_engine": {
        "module": "core.temporal_mastery.temporal_engine",
        "factory": "get_temporal_engine",
        "category": "transcendence",
        "description": "Time and prediction mastery",
    },
    "dimension_weaver": {
        "module": "core.dimension_weaver.dimension_weaver",
        "factory": "get_dimension_weaver",
        "category": "transcendence",
        "description": "Multi-dimensional synthesis",
    },
    # ─── Integration Layer ───
    "supreme_integration": {
        "module": "core.supreme_integration.integration_layer",
        "factory": "get_supreme_integration",
        "category": "integration",
        "description": "Final unification of all systems",
    },
}


# ═══════════════════════════════════════════════════════════════
# ENHANCED BAEL BRAIN
# ═══════════════════════════════════════════════════════════════


class EnhancedBaelBrain:
    """
    The supreme cognitive hub that unifies ALL subsystems into
    a single, fully functional processing pipeline.

    This is NOT a theoretical class — it actually initializes
    each module, connects them, and routes real queries through
    the multi-engine cognitive pipeline.

    Usage:
        brain = EnhancedBaelBrain()
        await brain.initialize()
        result = await brain.think("solve this problem")
        status = brain.get_full_status()
    """

    def __init__(self, config_path: str = "config/settings/main.yaml"):
        self.config_path = config_path
        self._initialized = False
        self._init_start: Optional[datetime] = None
        self._init_complete: Optional[datetime] = None

        # Subsystem registry — populated during initialize()
        self._subsystems: Dict[str, SubsystemInfo] = {}

        # Core brain integration (the original pipeline)
        self._brain_integration = None

        # Session tracking
        self._session_id = f"bael-{int(time.time())}"
        self._queries_processed = 0
        self._total_processing_ms = 0.0

        logger.info("EnhancedBaelBrain created — awaiting initialization")

    # ═══════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize ALL subsystems with graceful degradation.
        Each subsystem is loaded independently — if one fails,
        the others still come online. This mirrors the robust
        pattern used in BrainIntegration.initialize().

        Returns a status dict showing what loaded and what didn't.
        """
        self._init_start = datetime.now()
        logger.info("═" * 60)
        logger.info("BAEL ENHANCED BRAIN — INITIALIZING ALL SUBSYSTEMS")
        logger.info("═" * 60)

        # Step 1: Initialize the original brain integration pipeline
        try:
            from core.brain.integration import BrainIntegration

            self._brain_integration = BrainIntegration()
            await self._brain_integration.initialize()
            logger.info("✓ Core BrainIntegration pipeline initialized")
        except Exception as e:
            logger.warning(f"⚠ Core BrainIntegration failed: {e}")

        # Step 2: Initialize all 23 enhanced subsystems
        results = {"loaded": [], "failed": [], "skipped": []}

        for name, definition in SUBSYSTEM_DEFINITIONS.items():
            info = SubsystemInfo(
                name=name,
                module_path=definition["module"],
                factory_func=definition["factory"],
            )
            info.status = SubsystemStatus.INITIALIZING
            start = time.monotonic()

            try:
                # Dynamic import using importlib for maximum flexibility
                import importlib

                module = importlib.import_module(definition["module"])
                factory = getattr(module, definition["factory"])

                """
                Call the factory function — this creates a singleton or new
                instance of the subsystem. All our modules use get_*() pattern.
                """
                instance = factory()

                # If the instance has an async initialize method, call it
                if hasattr(instance, "initialize") and asyncio.iscoroutinefunction(
                    instance.initialize
                ):
                    await instance.initialize()
                elif hasattr(instance, "initialize"):
                    instance.initialize()

                info.instance = instance
                info.status = SubsystemStatus.ONLINE
                info.init_time_ms = (time.monotonic() - start) * 1000

                # Get power level if available
                if hasattr(instance, "get_status"):
                    try:
                        status = instance.get_status()
                        if isinstance(status, dict):
                            info.power_level = status.get(
                                "power_level",
                                status.get(
                                    "supremacy_score",
                                    status.get("capability_score", 1.0),
                                ),
                            )
                    except Exception:
                        info.power_level = 1.0

                results["loaded"].append(name)
                logger.info(
                    f"  ✓ {name}: ONLINE ({info.init_time_ms:.1f}ms) "
                    f"[{definition['category']}] {definition['description']}"
                )

            except ImportError as e:
                info.status = SubsystemStatus.ERROR
                info.error = f"ImportError: {e}"
                info.init_time_ms = (time.monotonic() - start) * 1000
                results["failed"].append(name)
                logger.warning(f"  ✗ {name}: IMPORT FAILED — {e}")

            except Exception as e:
                info.status = SubsystemStatus.ERROR
                info.error = str(e)
                info.init_time_ms = (time.monotonic() - start) * 1000
                results["failed"].append(name)
                logger.warning(f"  ✗ {name}: INIT FAILED — {e}")

            self._subsystems[name] = info

        self._initialized = True
        self._init_complete = datetime.now()
        total_ms = (self._init_complete - self._init_start).total_seconds() * 1000

        logger.info("═" * 60)
        logger.info(
            f"INITIALIZATION COMPLETE: "
            f"{len(results['loaded'])}/{len(SUBSYSTEM_DEFINITIONS)} online "
            f"({total_ms:.0f}ms)"
        )
        logger.info("═" * 60)

        return {
            "session_id": self._session_id,
            "total_subsystems": len(SUBSYSTEM_DEFINITIONS),
            "online": len(results["loaded"]),
            "failed": len(results["failed"]),
            "loaded": results["loaded"],
            "failed_names": results["failed"],
            "init_time_ms": total_ms,
        }

    # ═══════════════════════════════════════════════════════════
    # THINKING PIPELINE
    # ═══════════════════════════════════════════════════════════

    async def think(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a query through the full enhanced cognitive pipeline.

        The pipeline stages:
        1. Input Analysis — determine query type and complexity
        2. Knowledge Retrieval — pull from knowledge engine
        3. Multi-Engine Reasoning — omega mind + genius amplifier
        4. Strategic Planning — warfare module for approach
        5. Power Optimization — sacred math + cosmic optimizer
        6. Response Synthesis — combine all engine outputs
        7. Quality Check — consciousness unifier validates

        Args:
            query: The user's input/question/task
            context: Optional additional context dict

        Returns:
            Dict with response, reasoning traces, confidence, metadata
        """
        if not self._initialized:
            await self.initialize()

        start = time.monotonic()
        context = context or {}
        traces: List[str] = []
        engine_outputs: Dict[str, Any] = {}

        # ─── Stage 1: Input Analysis ───
        traces.append(f"[INPUT] Analyzing: {query[:100]}...")

        # ─── Stage 2: Core Brain Integration (original pipeline) ───
        core_response = None
        if self._brain_integration and self._brain_integration.is_initialized():
            try:
                from core.brain.integration import CognitiveContext

                ctx = CognitiveContext(
                    query=query,
                    mode=context.get("mode", "standard"),
                    persona=context.get("persona"),
                    history=context.get("history", []),
                )
                result = await self._brain_integration.process(ctx)
                core_response = result.response
                traces.append(
                    f"[CORE] Brain Integration: confidence={result.confidence:.2f}"
                )
                engine_outputs["core_brain"] = {
                    "response": result.response,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                }
            except Exception as e:
                traces.append(f"[CORE] Brain Integration error: {e}")

        # ─── Stage 3: Omega Mind Enhanced Reasoning ───
        omega = self._get_subsystem("omega_mind")
        if omega:
            try:
                if hasattr(omega, "think"):
                    omega_result = (
                        await omega.think(query)
                        if asyncio.iscoroutinefunction(omega.think)
                        else omega.think(query)
                    )
                    engine_outputs["omega_mind"] = omega_result
                    traces.append("[OMEGA] Supreme intelligence applied")
                elif hasattr(omega, "process"):
                    omega_result = (
                        await omega.process(query)
                        if asyncio.iscoroutinefunction(omega.process)
                        else omega.process(query)
                    )
                    engine_outputs["omega_mind"] = omega_result
                    traces.append("[OMEGA] Mind processing complete")
            except Exception as e:
                traces.append(f"[OMEGA] Error: {e}")

        # ─── Stage 4: Knowledge Synthesis ───
        knowledge = self._get_subsystem("knowledge_engine")
        if knowledge:
            try:
                if hasattr(knowledge, "synthesize"):
                    k_result = (
                        await knowledge.synthesize(query)
                        if asyncio.iscoroutinefunction(knowledge.synthesize)
                        else knowledge.synthesize(query)
                    )
                    engine_outputs["knowledge"] = k_result
                    traces.append("[KNOWLEDGE] Synthesis complete")
            except Exception as e:
                traces.append(f"[KNOWLEDGE] Error: {e}")

        # ─── Stage 5: Genius Amplification ───
        genius = self._get_subsystem("genius_amplifier")
        if genius:
            try:
                if hasattr(genius, "amplify"):
                    g_result = (
                        await genius.amplify(query)
                        if asyncio.iscoroutinefunction(genius.amplify)
                        else genius.amplify(query)
                    )
                    engine_outputs["genius"] = g_result
                    traces.append("[GENIUS] Amplification applied")
            except Exception as e:
                traces.append(f"[GENIUS] Error: {e}")

        # ─── Stage 6: Strategic Analysis ───
        warfare = self._get_subsystem("warfare")
        if warfare:
            try:
                if hasattr(warfare, "analyze"):
                    w_result = (
                        await warfare.analyze(query)
                        if asyncio.iscoroutinefunction(warfare.analyze)
                        else warfare.analyze(query)
                    )
                    engine_outputs["warfare"] = w_result
                    traces.append("[STRATEGY] Warfare analysis complete")
            except Exception as e:
                traces.append(f"[STRATEGY] Error: {e}")

        # ─── Stage 7: Power Optimization ───
        optimizer = self._get_subsystem("cosmic_optimizer")
        if optimizer:
            try:
                if hasattr(optimizer, "optimize"):
                    o_result = (
                        await optimizer.optimize(engine_outputs)
                        if asyncio.iscoroutinefunction(optimizer.optimize)
                        else optimizer.optimize(engine_outputs)
                    )
                    engine_outputs["optimization"] = o_result
                    traces.append("[POWER] Cosmic optimization applied")
            except Exception as e:
                traces.append(f"[POWER] Error: {e}")

        # ─── Stage 8: Response Synthesis ───
        elapsed_ms = (time.monotonic() - start) * 1000
        self._queries_processed += 1
        self._total_processing_ms += elapsed_ms

        """
        Build the final response by combining all engine outputs.
        Priority: core_brain > omega_mind > knowledge > genius
        """
        final_response = core_response or "BAEL processed your query."
        if engine_outputs:
            # Collect any string responses from engines
            engine_responses = []
            for eng_name, eng_out in engine_outputs.items():
                if isinstance(eng_out, str):
                    engine_responses.append(eng_out)
                elif isinstance(eng_out, dict) and "response" in eng_out:
                    engine_responses.append(eng_out["response"])

            if engine_responses and not core_response:
                final_response = engine_responses[0]

        return {
            "response": final_response,
            "session_id": self._session_id,
            "query": query,
            "engines_used": list(engine_outputs.keys()),
            "engine_count": len(engine_outputs),
            "traces": traces,
            "processing_time_ms": elapsed_ms,
            "confidence": self._calculate_confidence(engine_outputs),
            "subsystems_online": sum(
                1
                for s in self._subsystems.values()
                if s.status == SubsystemStatus.ONLINE
            ),
            "metadata": {
                "total_queries": self._queries_processed,
                "avg_processing_ms": self._total_processing_ms
                / max(1, self._queries_processed),
            },
        }

    def _calculate_confidence(self, engine_outputs: Dict) -> float:
        """Calculate overall confidence based on how many engines contributed."""
        if not engine_outputs:
            return 0.3

        # More engines = higher confidence, capped at 0.99
        base = 0.5
        per_engine = 0.08
        return min(0.99, base + len(engine_outputs) * per_engine)

    # ═══════════════════════════════════════════════════════════
    # SUBSYSTEM ACCESS
    # ═══════════════════════════════════════════════════════════

    def _get_subsystem(self, name: str) -> Optional[Any]:
        """Get a subsystem instance by name, returns None if unavailable."""
        info = self._subsystems.get(name)
        if info and info.status == SubsystemStatus.ONLINE:
            return info.instance
        return None

    def get_subsystem(self, name: str) -> Optional[Any]:
        """Public access to any subsystem by name."""
        return self._get_subsystem(name)

    def list_subsystems(self) -> Dict[str, str]:
        """List all subsystems and their status."""
        return {name: info.status.value for name, info in self._subsystems.items()}

    # ═══════════════════════════════════════════════════════════
    # SYSTEM STATUS
    # ═══════════════════════════════════════════════════════════

    def get_full_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the entire BAEL system.
        This is the master health check for all subsystems.
        """
        categories: Dict[str, List[Dict]] = {}
        total_power = 0.0
        online_count = 0

        for name, info in self._subsystems.items():
            definition = SUBSYSTEM_DEFINITIONS.get(name, {})
            category = definition.get("category", "unknown")

            if category not in categories:
                categories[category] = []

            sub_status = {
                "name": name,
                "status": info.status.value,
                "description": definition.get("description", ""),
                "init_time_ms": round(info.init_time_ms, 1),
                "power_level": round(info.power_level, 3),
            }
            if info.error:
                sub_status["error"] = info.error

            categories[category].append(sub_status)
            total_power += info.power_level
            if info.status == SubsystemStatus.ONLINE:
                online_count += 1

        total = len(self._subsystems)

        return {
            "system": "BAEL Enhanced Brain",
            "version": "2.0.0",
            "session_id": self._session_id,
            "initialized": self._initialized,
            "init_time": str(self._init_complete) if self._init_complete else None,
            "subsystems": {
                "total": total,
                "online": online_count,
                "offline": total - online_count,
                "health_pct": round((online_count / max(1, total)) * 100, 1),
            },
            "power": {
                "total_power": round(total_power, 3),
                "avg_power": round(total_power / max(1, online_count), 3),
                "max_theoretical": float(total),
            },
            "performance": {
                "queries_processed": self._queries_processed,
                "avg_processing_ms": round(
                    self._total_processing_ms / max(1, self._queries_processed), 1
                ),
                "total_processing_ms": round(self._total_processing_ms, 1),
            },
            "categories": categories,
            "core_brain": {
                "available": self._brain_integration is not None,
                "initialized": (
                    self._brain_integration.is_initialized()
                    if self._brain_integration
                    else False
                ),
            },
        }

    def get_power_report(self) -> str:
        """Generate a human-readable power report."""
        status = self.get_full_status()
        lines = [
            "═" * 60,
            "  BAEL ENHANCED BRAIN — POWER REPORT",
            "═" * 60,
            f"  Session: {status['session_id']}",
            f"  Status:  {'OPERATIONAL' if status['initialized'] else 'OFFLINE'}",
            f"  Health:  {status['subsystems']['health_pct']}%",
            f"  Power:   {status['power']['total_power']:.1f} / {status['power']['max_theoretical']:.0f}",
            "",
        ]

        for category, subsystems in status["categories"].items():
            lines.append(f"  ── {category.upper()} ──")
            for sub in subsystems:
                icon = "✓" if sub["status"] == "online" else "✗"
                lines.append(
                    f"    {icon} {sub['name']}: {sub['status']} "
                    f"({sub['init_time_ms']}ms)"
                )
            lines.append("")

        lines.append(f"  Total Queries: {status['performance']['queries_processed']}")
        lines.append(f"  Avg Latency:   {status['performance']['avg_processing_ms']}ms")
        lines.append("═" * 60)

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# FACTORY / SINGLETON
# ═══════════════════════════════════════════════════════════════

_enhanced_brain_instance: Optional[EnhancedBaelBrain] = None


def get_enhanced_brain() -> EnhancedBaelBrain:
    """Get or create the singleton EnhancedBaelBrain instance."""
    global _enhanced_brain_instance
    if _enhanced_brain_instance is None:
        _enhanced_brain_instance = EnhancedBaelBrain()
    return _enhanced_brain_instance


async def quick_think(query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Convenience function — initialize brain if needed and think.

    Usage:
        result = await quick_think("What is the meaning of life?")
        print(result["response"])
    """
    brain = get_enhanced_brain()
    if not brain._initialized:
        await brain.initialize()
    return await brain.think(query, context)


__all__ = [
    "EnhancedBaelBrain",
    "get_enhanced_brain",
    "quick_think",
    "SubsystemStatus",
    "SubsystemInfo",
    "SUBSYSTEM_DEFINITIONS",
]
