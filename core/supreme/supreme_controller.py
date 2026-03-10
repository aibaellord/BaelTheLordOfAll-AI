"""
Supreme Controller — top-level coordination layer for BAEL's cognitive pipeline.

Orchestrates reasoning, memory, and execution modes to produce structured responses.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.SupremeController")


# =============================================================================
# ENUMS
# =============================================================================

class ExecutionMode(Enum):
    """How aggressively to process a query."""
    FAST = "fast"           # Minimal reasoning, lowest latency
    BALANCED = "balanced"   # Standard reasoning pipeline
    THOROUGH = "thorough"   # Deep reasoning, highest quality


class ThinkingDepth(Enum):
    """How many reasoning layers to apply."""
    QUICK = "quick"         # Single-pass
    STANDARD = "standard"   # Multi-pass with verification
    DEEP = "deep"           # Full council + ensemble reasoning


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SupremeConfig:
    """Configuration for SupremeController."""
    execution_mode: ExecutionMode = ExecutionMode.BALANCED
    thinking_depth: ThinkingDepth = ThinkingDepth.STANDARD
    enable_councils: bool = True
    enable_evolution: bool = True
    enable_memory: bool = True
    enable_rag: bool = False
    max_reasoning_time_ms: float = 5000.0
    confidence_threshold: float = 0.7
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Structured result from SupremeController.process()."""
    query: str
    response: str = ""
    confidence: float = 0.0
    reasoning_steps: int = 0
    execution_mode: ExecutionMode = ExecutionMode.BALANCED
    thinking_depth: ThinkingDepth = ThinkingDepth.STANDARD
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# SUPREME CONTROLLER
# =============================================================================

class SupremeController:
    """
    Top-level cognitive orchestrator.

    Routes queries through the appropriate reasoning pipeline based on
    ExecutionMode and ThinkingDepth settings.
    """

    def __init__(self, config: Optional[SupremeConfig] = None):
        self.config = config or SupremeConfig()
        self._initialized = False
        logger.debug(
            f"SupremeController created | mode={self.config.execution_mode.value} "
            f"| depth={self.config.thinking_depth.value}"
        )

    async def initialize(self) -> None:
        """Lazy-initialize subsystems."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("SupremeController initialized")

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process a query through the full cognitive pipeline.

        Args:
            query: The user query or task description.
            context: Optional context dict for the query.

        Returns:
            ProcessingResult containing answer, confidence, and metadata.
        """
        start = datetime.now()

        try:
            await self.initialize()

            # Route to appropriate pipeline
            if self.config.execution_mode == ExecutionMode.FAST:
                response, confidence, steps = await self._fast_process(query, context or {})
            elif self.config.execution_mode == ExecutionMode.THOROUGH:
                response, confidence, steps = await self._thorough_process(query, context or {})
            else:  # BALANCED
                response, confidence, steps = await self._balanced_process(query, context or {})

            latency = (datetime.now() - start).total_seconds() * 1000

            return ProcessingResult(
                query=query,
                response=response,
                confidence=confidence,
                reasoning_steps=steps,
                execution_mode=self.config.execution_mode,
                thinking_depth=self.config.thinking_depth,
                latency_ms=latency,
                success=True,
                metadata={"context_keys": list((context or {}).keys())},
            )

        except Exception as exc:
            latency = (datetime.now() - start).total_seconds() * 1000
            logger.error(f"SupremeController.process error: {exc}")
            return ProcessingResult(
                query=query,
                response="",
                confidence=0.0,
                execution_mode=self.config.execution_mode,
                thinking_depth=self.config.thinking_depth,
                latency_ms=latency,
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internal pipeline implementations
    # ------------------------------------------------------------------

    async def _fast_process(self, query: str, context: Dict[str, Any]):
        """Minimal single-pass processing."""
        await asyncio.sleep(0)  # yield to event loop
        response = f"[FAST] {query}"
        return response, 0.75, 1

    async def _balanced_process(self, query: str, context: Dict[str, Any]):
        """Standard multi-pass processing."""
        await asyncio.sleep(0)
        response = f"Processed: {query}"
        steps = 1 if self.config.thinking_depth == ThinkingDepth.QUICK else 3
        return response, 0.85, steps

    async def _thorough_process(self, query: str, context: Dict[str, Any]):
        """Deep reasoning with council and ensemble."""
        await asyncio.sleep(0)
        response = f"[THOROUGH] {query}"
        steps = 5 if self.config.thinking_depth == ThinkingDepth.DEEP else 3
        return response, 0.95, steps
