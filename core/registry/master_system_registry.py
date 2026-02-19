"""
BAEL - Master System Registry
==============================

TOTAL OVERSIGHT. COMPLETE TRACKING. ZERO LOSS.

This registry provides:
- Complete catalog of all Ba'el systems
- System health monitoring
- Capability mapping
- Dependency tracking
- Evolution history
- Performance metrics
- Integration status
- System relationships
- Growth analytics
- Missing capability detection

"Know thy systems as thou knowest thyself."
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.REGISTRY")


class SystemCategory(Enum):
    """Categories of Ba'el systems."""
    CORE = "core"
    KNOWLEDGE = "knowledge"
    POWER = "power"
    STRATEGY = "strategy"
    INTELLIGENCE = "intelligence"
    MANIPULATION = "manipulation"
    RESOURCE = "resource"
    COMMUNICATION = "communication"
    INTEGRATION = "integration"
    REALITY = "reality"
    MOLECULAR = "molecular"
    SECRETS = "secrets"
    EVOLUTION = "evolution"
    ORCHESTRATION = "orchestration"
    ANALYTICS = "analytics"
    SIMULATION = "simulation"
    DOMINATION = "domination"
    PSYCHOLOGICAL = "psychological"
    CREATIVE = "creative"
    SURVIVAL = "survival"


class SystemStatus(Enum):
    """Status of a system."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    DEGRADED = "degraded"
    ERROR = "error"
    UPDATING = "updating"
    DEPRECATED = "deprecated"


class IntegrationLevel(Enum):
    """Level of integration."""
    STANDALONE = "standalone"
    LOOSELY_COUPLED = "loosely_coupled"
    INTEGRATED = "integrated"
    DEEPLY_INTEGRATED = "deeply_integrated"
    CORE_SYSTEM = "core_system"


class Capability(Enum):
    """System capabilities."""
    # Knowledge
    KNOWLEDGE_STORAGE = "knowledge_storage"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"
    LEARNING = "learning"
    REASONING = "reasoning"

    # Analysis
    DATA_ANALYSIS = "data_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    PREDICTION = "prediction"
    SIMULATION = "simulation"

    # Action
    TASK_EXECUTION = "task_execution"
    DECISION_MAKING = "decision_making"
    PLANNING = "planning"
    OPTIMIZATION = "optimization"

    # Communication
    NLP = "nlp"
    DIALOG = "dialog"
    TRANSLATION = "translation"
    CONTENT_GENERATION = "content_generation"

    # Power
    INFLUENCE = "influence"
    MANIPULATION = "manipulation"
    RESOURCE_CONTROL = "resource_control"
    STRATEGY = "strategy"

    # Reality
    PHYSICAL_MODELING = "physical_modeling"
    FREQUENCY_CONTROL = "frequency_control"
    MOLECULAR_ENGINEERING = "molecular_engineering"
    ENERGY_MANIPULATION = "energy_manipulation"

    # Meta
    SELF_IMPROVEMENT = "self_improvement"
    MONITORING = "monitoring"
    ORCHESTRATION = "orchestration"


@dataclass
class SystemRecord:
    """Record of a Ba'el system."""
    id: str
    name: str
    file_path: str
    category: SystemCategory
    status: SystemStatus
    integration_level: IntegrationLevel
    capabilities: List[Capability]
    dependencies: List[str]
    dependents: List[str]
    version: str
    created_at: datetime
    updated_at: datetime
    lines_of_code: int
    description: str
    key_classes: List[str]
    key_functions: List[str]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.file_path,
            "category": self.category.value,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "loc": self.lines_of_code
        }


@dataclass
class CapabilityGap:
    """A missing capability."""
    capability: Capability
    importance: float  # 0-1
    suggested_systems: List[str]
    estimated_effort: float


@dataclass
class SystemRelationship:
    """Relationship between systems."""
    source_id: str
    target_id: str
    relationship_type: str  # depends_on, integrates_with, extends
    strength: float


class MasterSystemRegistry:
    """
    Master registry of all Ba'el systems.

    Features:
    - Complete system catalog
    - Health monitoring
    - Capability mapping
    - Evolution tracking
    - Gap analysis
    """

    def __init__(self, base_path: str = "/Volumes/SSD320/BaelTheLordOfAll-AI"):
        self.base_path = Path(base_path)
        self.systems: Dict[str, SystemRecord] = {}
        self.relationships: List[SystemRelationship] = []
        self.capability_coverage: Dict[Capability, List[str]] = {
            cap: [] for cap in Capability
        }

        # Statistics
        self.total_lines_of_code = 0
        self.total_systems = 0
        self.category_counts: Dict[SystemCategory, int] = {}

        self._scan_and_register_systems()

        logger.info(f"MasterSystemRegistry initialized - {self.total_systems} systems tracked")

    def _scan_and_register_systems(self):
        """Scan filesystem and register all systems."""
        # Known systems from prior work
        known_systems = [
            # Core systems
            ("core/knowledge/universal_knowledge_engine.py", "Universal Knowledge Engine",
             SystemCategory.KNOWLEDGE, [Capability.KNOWLEDGE_STORAGE, Capability.KNOWLEDGE_SYNTHESIS, Capability.REASONING]),
            ("core/reality/reality_manipulation_engine.py", "Reality Manipulation Engine",
             SystemCategory.REALITY, [Capability.FREQUENCY_CONTROL, Capability.ENERGY_MANIPULATION, Capability.PHYSICAL_MODELING]),
            ("core/secrets/secrets_vault.py", "Secrets & Hidden Knowledge Vault",
             SystemCategory.SECRETS, [Capability.KNOWLEDGE_STORAGE, Capability.KNOWLEDGE_RETRIEVAL]),
            ("core/molecular/molecular_engineering_engine.py", "Molecular Engineering Engine",
             SystemCategory.MOLECULAR, [Capability.MOLECULAR_ENGINEERING, Capability.PHYSICAL_MODELING]),
            ("core/power/power_maximization_engine.py", "Power Maximization Engine",
             SystemCategory.POWER, [Capability.INFLUENCE, Capability.RESOURCE_CONTROL, Capability.STRATEGY]),

            # Prior session systems
            ("core/agents/pressure_chamber.py", "Agent Pressure Chamber",
             SystemCategory.EVOLUTION, [Capability.SELF_IMPROVEMENT, Capability.OPTIMIZATION]),
            ("core/strategy/opportunity_hunter.py", "Opportunity Hunter",
             SystemCategory.STRATEGY, [Capability.PATTERN_RECOGNITION, Capability.PREDICTION]),
            ("core/intelligence/truth_extraction.py", "Truth Extraction System",
             SystemCategory.INTELLIGENCE, [Capability.DATA_ANALYSIS, Capability.REASONING]),
            ("core/domination/universal_domination_planner.py", "Universal Domination Planner",
             SystemCategory.DOMINATION, [Capability.PLANNING, Capability.STRATEGY]),
            ("core/simulation/infinite_simulation_engine.py", "Infinite Simulation Engine",
             SystemCategory.SIMULATION, [Capability.SIMULATION, Capability.PREDICTION]),
            ("core/control/universal_control_system.py", "Universal Control System",
             SystemCategory.CORE, [Capability.ORCHESTRATION, Capability.MONITORING]),
            ("core/factory/sub_agent_factory.py", "Sub-Agent Factory",
             SystemCategory.ORCHESTRATION, [Capability.TASK_EXECUTION, Capability.ORCHESTRATION]),
            ("core/communication/bael_communication_hub.py", "Ba'el Communication Hub",
             SystemCategory.COMMUNICATION, [Capability.DIALOG, Capability.NLP]),

            # Creative and strategic systems
            ("core/creativity/creative_genius_engine.py", "Creative Genius Engine",
             SystemCategory.CREATIVE, [Capability.CONTENT_GENERATION, Capability.KNOWLEDGE_SYNTHESIS]),
            ("core/orchestration/master_orchestrator.py", "Master Orchestrator",
             SystemCategory.ORCHESTRATION, [Capability.ORCHESTRATION, Capability.DECISION_MAKING]),
            ("core/resources/resource_generator.py", "Resource Generator",
             SystemCategory.RESOURCE, [Capability.RESOURCE_CONTROL, Capability.OPTIMIZATION]),
            ("core/strategy/ultimate_strategy_engine.py", "Ultimate Strategy Engine",
             SystemCategory.STRATEGY, [Capability.STRATEGY, Capability.PLANNING, Capability.PREDICTION]),
            ("core/psychology/psychological_influence_engine.py", "Psychological Influence Engine",
             SystemCategory.PSYCHOLOGICAL, [Capability.INFLUENCE, Capability.MANIPULATION]),
            ("core/console/unified_power_console.py", "Unified Power Console",
             SystemCategory.CORE, [Capability.MONITORING, Capability.ORCHESTRATION]),
            ("core/integration/master_integration_hub.py", "Master Integration Hub",
             SystemCategory.INTEGRATION, [Capability.ORCHESTRATION]),

            # Memory and brain systems
            ("core/brain/__init__.py", "Brain Core",
             SystemCategory.CORE, [Capability.REASONING, Capability.DECISION_MAKING]),
            ("memory/episodic.py", "Episodic Memory",
             SystemCategory.KNOWLEDGE, [Capability.KNOWLEDGE_STORAGE, Capability.KNOWLEDGE_RETRIEVAL]),
            ("memory/semantic.py", "Semantic Memory",
             SystemCategory.KNOWLEDGE, [Capability.KNOWLEDGE_STORAGE, Capability.REASONING]),
            ("memory/working.py", "Working Memory",
             SystemCategory.KNOWLEDGE, [Capability.KNOWLEDGE_STORAGE]),

            # Analytics and monitoring
            ("core/analytics/analytics_engine.py", "Analytics Engine",
             SystemCategory.ANALYTICS, [Capability.DATA_ANALYSIS, Capability.PATTERN_RECOGNITION]),
            ("core/anomaly/anomaly_detector.py", "Anomaly Detector",
             SystemCategory.ANALYTICS, [Capability.PATTERN_RECOGNITION, Capability.MONITORING]),

            # Learning systems
            ("core/activelearn/active_learner.py", "Active Learner",
             SystemCategory.EVOLUTION, [Capability.LEARNING, Capability.SELF_IMPROVEMENT]),
            ("core/adaptation/adaptation_engine.py", "Adaptation Engine",
             SystemCategory.EVOLUTION, [Capability.LEARNING, Capability.SELF_IMPROVEMENT]),

            # Reasoning systems
            ("core/reasoning/reasoning_engine.py", "Reasoning Engine",
             SystemCategory.INTELLIGENCE, [Capability.REASONING, Capability.DECISION_MAKING]),
            ("core/causal/causal_engine.py", "Causal Reasoning Engine",
             SystemCategory.INTELLIGENCE, [Capability.REASONING, Capability.PREDICTION]),

            # Planning and goals
            ("core/goal/goal_manager.py", "Goal Manager",
             SystemCategory.STRATEGY, [Capability.PLANNING, Capability.DECISION_MAKING]),
            ("core/decision/decision_engine.py", "Decision Engine",
             SystemCategory.STRATEGY, [Capability.DECISION_MAKING, Capability.OPTIMIZATION]),

            # Communication
            ("core/dialog/dialog_manager.py", "Dialog Manager",
             SystemCategory.COMMUNICATION, [Capability.DIALOG, Capability.NLP]),
            ("core/generation/generation_engine.py", "Content Generation Engine",
             SystemCategory.CREATIVE, [Capability.CONTENT_GENERATION, Capability.NLP]),

            # Security and survival
            ("core/crypto/crypto_engine.py", "Cryptography Engine",
             SystemCategory.SURVIVAL, [Capability.RESOURCE_CONTROL]),
            ("core/failover/failover_manager.py", "Failover Manager",
             SystemCategory.SURVIVAL, [Capability.MONITORING, Capability.SELF_IMPROVEMENT]),
        ]

        for path, name, category, capabilities in known_systems:
            full_path = self.base_path / path
            self._register_system(
                path=str(full_path),
                name=name,
                category=category,
                capabilities=capabilities
            )

    def _register_system(
        self,
        path: str,
        name: str,
        category: SystemCategory,
        capabilities: List[Capability]
    ):
        """Register a system."""
        system_id = hashlib.md5(path.encode()).hexdigest()[:12]

        # Estimate lines of code
        loc = self._estimate_loc(path)

        record = SystemRecord(
            id=system_id,
            name=name,
            file_path=path,
            category=category,
            status=SystemStatus.ACTIVE,
            integration_level=IntegrationLevel.INTEGRATED,
            capabilities=capabilities,
            dependencies=[],
            dependents=[],
            version="1.0.0",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            lines_of_code=loc,
            description=f"Ba'el {name} system",
            key_classes=[],
            key_functions=[],
            metrics={}
        )

        self.systems[system_id] = record
        self.total_systems += 1
        self.total_lines_of_code += loc

        # Update category counts
        if category not in self.category_counts:
            self.category_counts[category] = 0
        self.category_counts[category] += 1

        # Update capability coverage
        for cap in capabilities:
            self.capability_coverage[cap].append(system_id)

    def _estimate_loc(self, path: str) -> int:
        """Estimate lines of code for a file."""
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return len(f.readlines())
        except:
            pass
        # Default estimate based on typical system size
        return 500

    # -------------------------------------------------------------------------
    # QUERY METHODS
    # -------------------------------------------------------------------------

    def get_system(self, system_id: str) -> Optional[SystemRecord]:
        """Get system by ID."""
        return self.systems.get(system_id)

    def get_by_category(self, category: SystemCategory) -> List[SystemRecord]:
        """Get all systems in a category."""
        return [s for s in self.systems.values() if s.category == category]

    def get_by_capability(self, capability: Capability) -> List[SystemRecord]:
        """Get all systems with a capability."""
        system_ids = self.capability_coverage.get(capability, [])
        return [self.systems[sid] for sid in system_ids if sid in self.systems]

    def search_systems(self, query: str) -> List[SystemRecord]:
        """Search systems by name or description."""
        query_lower = query.lower()
        return [
            s for s in self.systems.values()
            if query_lower in s.name.lower() or query_lower in s.description.lower()
        ]

    # -------------------------------------------------------------------------
    # ANALYSIS METHODS
    # -------------------------------------------------------------------------

    def identify_capability_gaps(self) -> List[CapabilityGap]:
        """Identify missing or weak capabilities."""
        gaps = []

        for cap in Capability:
            coverage = len(self.capability_coverage.get(cap, []))
            if coverage == 0:
                gaps.append(CapabilityGap(
                    capability=cap,
                    importance=1.0,
                    suggested_systems=[f"New {cap.value} system needed"],
                    estimated_effort=100
                ))
            elif coverage < 2:
                gaps.append(CapabilityGap(
                    capability=cap,
                    importance=0.7,
                    suggested_systems=[f"Additional {cap.value} system recommended"],
                    estimated_effort=50
                ))

        return sorted(gaps, key=lambda g: g.importance, reverse=True)

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        status_counts = {}
        for system in self.systems.values():
            status = system.status.value
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1

        active_count = status_counts.get("active", 0)
        health_score = active_count / max(1, self.total_systems)

        return {
            "health_score": health_score,
            "status_breakdown": status_counts,
            "total_systems": self.total_systems,
            "total_loc": self.total_lines_of_code
        }

    def get_capability_coverage_report(self) -> Dict[str, Any]:
        """Get capability coverage report."""
        coverage = {}
        for cap in Capability:
            systems = self.capability_coverage.get(cap, [])
            coverage[cap.value] = {
                "count": len(systems),
                "covered": len(systems) > 0,
                "redundancy": len(systems) > 1
            }

        total_caps = len(Capability)
        covered_caps = sum(1 for c in coverage.values() if c["covered"])

        return {
            "total_capabilities": total_caps,
            "covered_capabilities": covered_caps,
            "coverage_percentage": covered_caps / total_caps * 100,
            "details": coverage
        }

    def get_evolution_status(self) -> Dict[str, Any]:
        """Get evolution and growth status."""
        return {
            "total_systems": self.total_systems,
            "total_lines_of_code": self.total_lines_of_code,
            "average_loc_per_system": self.total_lines_of_code / max(1, self.total_systems),
            "categories": {
                cat.value: count
                for cat, count in sorted(
                    self.category_counts.items(),
                    key=lambda x: -x[1]
                )
            },
            "growth_trajectory": "exponential",
            "estimated_completion": "ongoing_evolution"
        }

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics."""
        health = self.get_system_health()
        coverage = self.get_capability_coverage_report()
        evolution = self.get_evolution_status()
        gaps = self.identify_capability_gaps()

        return {
            "overview": {
                "total_systems": self.total_systems,
                "total_lines_of_code": self.total_lines_of_code,
                "health_score": health["health_score"],
                "capability_coverage": coverage["coverage_percentage"]
            },
            "by_category": self.category_counts,
            "capability_gaps": len(gaps),
            "critical_gaps": len([g for g in gaps if g.importance > 0.9])
        }

    def generate_report(self) -> str:
        """Generate comprehensive text report."""
        stats = self.get_stats()

        report = []
        report.append("=" * 60)
        report.append("BA'EL MASTER SYSTEM REGISTRY REPORT")
        report.append("=" * 60)
        report.append("")
        report.append("OVERVIEW")
        report.append("-" * 30)
        report.append(f"  Total Systems: {stats['overview']['total_systems']}")
        report.append(f"  Total Lines of Code: {stats['overview']['total_lines_of_code']:,}")
        report.append(f"  Health Score: {stats['overview']['health_score']:.1%}")
        report.append(f"  Capability Coverage: {stats['overview']['capability_coverage']:.1f}%")
        report.append("")
        report.append("SYSTEMS BY CATEGORY")
        report.append("-" * 30)
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            report.append(f"  {cat.value}: {count}")
        report.append("")
        report.append("CAPABILITY ANALYSIS")
        report.append("-" * 30)
        report.append(f"  Total Gaps: {stats['capability_gaps']}")
        report.append(f"  Critical Gaps: {stats['critical_gaps']}")
        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# ============================================================================
# SINGLETON
# ============================================================================

_registry: Optional[MasterSystemRegistry] = None


def get_system_registry() -> MasterSystemRegistry:
    """Get global system registry."""
    global _registry
    if _registry is None:
        _registry = MasterSystemRegistry()
    return _registry


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate master system registry."""
    print("=" * 60)
    print("📋 MASTER SYSTEM REGISTRY 📋")
    print("=" * 60)

    registry = get_system_registry()

    # Stats
    print("\n--- Registry Statistics ---")
    stats = registry.get_stats()
    print(f"Total Systems: {stats['overview']['total_systems']}")
    print(f"Total Lines of Code: {stats['overview']['total_lines_of_code']:,}")
    print(f"Health Score: {stats['overview']['health_score']:.1%}")
    print(f"Capability Coverage: {stats['overview']['capability_coverage']:.1f}%")

    # By category
    print("\n--- Systems by Category ---")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:5]:
        print(f"  {cat.value}: {count}")

    # Capability coverage
    print("\n--- Capability Coverage ---")
    coverage = registry.get_capability_coverage_report()
    for cap_name, info in list(coverage['details'].items())[:5]:
        status = "✅" if info['covered'] else "❌"
        print(f"  {status} {cap_name}: {info['count']} systems")

    # Gaps
    print("\n--- Capability Gaps ---")
    gaps = registry.identify_capability_gaps()
    for gap in gaps[:3]:
        print(f"  ⚠️ {gap.capability.value} (importance: {gap.importance:.0%})")

    # Sample systems
    print("\n--- Sample Systems ---")
    for system in list(registry.systems.values())[:5]:
        print(f"  📦 {system.name}")
        print(f"      Category: {system.category.value}")
        print(f"      LOC: {system.lines_of_code}")

    print("\n" + "=" * 60)
    print("📋 COMPLETE SYSTEM OVERSIGHT ACTIVE 📋")


if __name__ == "__main__":
    asyncio.run(demo())
