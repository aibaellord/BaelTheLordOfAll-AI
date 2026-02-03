"""
BAEL Supreme Controller - The Unified Orchestration Layer

This is the master integration layer that wires together all 430+ BAEL modules
into a coherent, intelligent system. It is the "brain of the brain" - the
meta-controller that:

1. Routes queries to appropriate reasoning engines (25+ types)
2. Manages the 5-layer cognitive memory architecture
3. Orchestrates multi-agent councils for complex decisions
4. Drives the self-evolution and learning loops
5. Enforces zero-cost operation through provider cycling

This is what makes BAEL a unified intelligence rather than a collection of parts.
"""

from .cognitive_pipeline import CognitivePipeline, MemoryLayer
from .council_orchestrator import CouncilOrchestrator
from .integration_hub import IntegrationHub
from .orchestrator import ControllerConfig, SupremeController
from .reasoning_cascade import ReasoningCascade, ReasoningMode

__all__ = [
    "SupremeController",
    "ControllerConfig",
    "ReasoningCascade",
    "ReasoningMode",
    "CognitivePipeline",
    "MemoryLayer",
    "CouncilOrchestrator",
    "IntegrationHub",
]
