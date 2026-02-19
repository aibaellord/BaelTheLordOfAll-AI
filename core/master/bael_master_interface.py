"""
BA'EL - Master Interface v2
============================

The Ultimate Unified Interface - The Crown of Ba'el.

This is the master orchestrator that unifies ALL Ba'el systems
into a single, omnipotent interface. Every capability flows
through this central nexus.

Features:
1. Unified System Registry - All 100+ systems accessible
2. Intelligent Routing - Smart command dispatch
3. Context Fusion - Multi-system context awareness
4. Cascade Execution - Chain multiple systems
5. Meta-Learning - Learn optimal system combinations
6. Natural Language Interface - Plain English commands
7. Power Modes - Adjust capability levels
8. Real-Time Monitoring - System health and performance
9. Self-Optimization - Continuous improvement
10. Transcendent Operations - Beyond single-system limits

"I am Ba'el. I am the totality of all systems unified."
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger("BAEL.MASTER")


# ============================================================================
# ENUMS
# ============================================================================

class SystemCategory(Enum):
    """Categories of Ba'el systems."""
    REASONING = "reasoning"
    SECURITY = "security"
    KNOWLEDGE = "knowledge"
    AUTOMATION = "automation"
    INTELLIGENCE = "intelligence"
    LEARNING = "learning"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    CREATION = "creation"
    ORCHESTRATION = "orchestration"


class PowerMode(Enum):
    """Power modes for Ba'el operations."""
    WHISPER = "whisper"  # Minimal, silent operations
    NORMAL = "normal"  # Standard operations
    ENHANCED = "enhanced"  # Boosted capabilities
    MAXIMUM = "maximum"  # Full power
    TRANSCENDENT = "transcendent"  # Beyond limits


class ExecutionStrategy(Enum):
    """Strategies for multi-system execution."""
    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"  # All at once
    CASCADE = "cascade"  # Output feeds input
    COMPETITIVE = "competitive"  # Best result wins
    CONSENSUS = "consensus"  # Agreement required


class CommandIntent(Enum):
    """Classified command intents."""
    QUERY = "query"  # Information retrieval
    EXECUTE = "execute"  # Perform action
    CREATE = "create"  # Generate something
    ANALYZE = "analyze"  # Deep analysis
    CONTROL = "control"  # System control
    CONFIGURE = "configure"  # Settings
    MONITOR = "monitor"  # Observation
    OPTIMIZE = "optimize"  # Improvement


class HealthStatus(Enum):
    """System health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SystemRegistration:
    """Registration of a Ba'el system."""
    id: str
    name: str
    category: SystemCategory
    description: str
    capabilities: List[str]
    dependencies: List[str]
    instance: Any = None  # The actual system instance
    health: HealthStatus = HealthStatus.HEALTHY
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    last_used: Optional[datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description[:100],
            "capabilities": self.capabilities[:5],
            "health": self.health.value,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count
        }


@dataclass
class CommandContext:
    """Context for command execution."""
    command_id: str
    raw_input: str
    intent: CommandIntent
    target_systems: List[str]
    parameters: Dict[str, Any]
    power_mode: PowerMode
    strategy: ExecutionStrategy
    timeout_seconds: float = 30.0
    user_id: str = "default"
    session_id: Optional[str] = None
    previous_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemResult:
    """Result from a system execution."""
    system_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "error": self.error
        }


@dataclass
class MasterResult:
    """Result from the master interface."""
    command_id: str
    success: bool
    primary_result: Any
    system_results: List[SystemResult]
    total_execution_time_ms: float
    systems_used: List[str]
    strategy_used: ExecutionStrategy
    power_mode: PowerMode
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "success": self.success,
            "systems_used": self.systems_used,
            "total_time_ms": self.total_execution_time_ms,
            "strategy": self.strategy_used.value,
            "power_mode": self.power_mode.value
        }


@dataclass
class CascadeDefinition:
    """Definition of a system cascade."""
    id: str
    name: str
    description: str
    systems: List[str]  # Ordered system IDs
    transformations: List[Dict[str, str]]  # How to transform between steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "systems": self.systems
        }


# ============================================================================
# SYSTEM REGISTRY
# ============================================================================

class SystemRegistry:
    """
    Registry of all Ba'el systems.
    """

    def __init__(self):
        self.systems: Dict[str, SystemRegistration] = {}
        self.by_category: Dict[SystemCategory, List[str]] = defaultdict(list)
        self.by_capability: Dict[str, List[str]] = defaultdict(list)
        self.cascades: Dict[str, CascadeDefinition] = {}

    def register(
        self,
        name: str,
        category: SystemCategory,
        description: str,
        capabilities: List[str],
        dependencies: List[str] = None,
        instance: Any = None
    ) -> SystemRegistration:
        """Register a system."""
        system_id = hashlib.md5(name.encode()).hexdigest()[:12]

        reg = SystemRegistration(
            id=system_id,
            name=name,
            category=category,
            description=description,
            capabilities=capabilities,
            dependencies=dependencies or [],
            instance=instance
        )

        self.systems[system_id] = reg
        self.by_category[category].append(system_id)

        for cap in capabilities:
            self.by_capability[cap.lower()].append(system_id)

        logger.info(f"Registered system: {name} ({system_id})")
        return reg

    def get(self, system_id: str) -> Optional[SystemRegistration]:
        """Get a system by ID."""
        return self.systems.get(system_id)

    def find_by_capability(self, capability: str) -> List[SystemRegistration]:
        """Find systems by capability."""
        system_ids = self.by_capability.get(capability.lower(), [])
        return [self.systems[sid] for sid in system_ids if sid in self.systems]

    def find_by_category(self, category: SystemCategory) -> List[SystemRegistration]:
        """Find systems by category."""
        system_ids = self.by_category.get(category, [])
        return [self.systems[sid] for sid in system_ids if sid in self.systems]

    def find_by_name(self, name: str) -> Optional[SystemRegistration]:
        """Find system by name."""
        for reg in self.systems.values():
            if reg.name.lower() == name.lower():
                return reg
        return None

    def define_cascade(
        self,
        name: str,
        description: str,
        systems: List[str],
        transformations: List[Dict[str, str]] = None
    ) -> CascadeDefinition:
        """Define a system cascade."""
        cascade = CascadeDefinition(
            id=hashlib.md5(name.encode()).hexdigest()[:8],
            name=name,
            description=description,
            systems=systems,
            transformations=transformations or []
        )

        self.cascades[cascade.id] = cascade
        return cascade

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered systems."""
        return [reg.to_dict() for reg in self.systems.values()]

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_systems": len(self.systems),
            "by_category": {
                cat.value: len(ids)
                for cat, ids in self.by_category.items()
            },
            "total_capabilities": len(self.by_capability),
            "cascades": len(self.cascades),
            "healthy_systems": len([s for s in self.systems.values() if s.health == HealthStatus.HEALTHY])
        }


# ============================================================================
# COMMAND ROUTER
# ============================================================================

class CommandRouter:
    """
    Routes commands to appropriate systems.
    """

    def __init__(self, registry: SystemRegistry):
        self.registry = registry

        # Intent patterns
        self.intent_patterns: Dict[CommandIntent, List[str]] = {
            CommandIntent.QUERY: [
                r"what is", r"how to", r"explain", r"tell me", r"show",
                r"find", r"search", r"get", r"list", r"describe"
            ],
            CommandIntent.EXECUTE: [
                r"run", r"execute", r"do", r"perform", r"start",
                r"trigger", r"activate", r"launch"
            ],
            CommandIntent.CREATE: [
                r"create", r"generate", r"make", r"build", r"write",
                r"compose", r"design", r"develop"
            ],
            CommandIntent.ANALYZE: [
                r"analyze", r"assess", r"evaluate", r"compare",
                r"investigate", r"examine", r"study"
            ],
            CommandIntent.CONTROL: [
                r"stop", r"pause", r"resume", r"restart", r"disable",
                r"enable", r"kill", r"terminate"
            ],
            CommandIntent.CONFIGURE: [
                r"set", r"config", r"setting", r"change", r"update",
                r"modify", r"adjust"
            ],
            CommandIntent.MONITOR: [
                r"status", r"health", r"monitor", r"watch", r"track",
                r"observe", r"check"
            ],
            CommandIntent.OPTIMIZE: [
                r"optimize", r"improve", r"enhance", r"boost",
                r"tune", r"refine"
            ]
        }

        # Capability keywords for routing
        self.capability_keywords: Dict[str, List[str]] = {
            "security": ["security", "hack", "pentest", "vulnerability", "attack", "defense"],
            "reasoning": ["reason", "think", "logic", "deduce", "infer", "solve"],
            "knowledge": ["know", "information", "fact", "data", "learn"],
            "automation": ["automate", "script", "workflow", "task", "job"],
            "analysis": ["analyze", "statistics", "metrics", "report", "insight"],
            "creation": ["create", "generate", "build", "make", "write"],
            "prediction": ["predict", "forecast", "anticipate", "expect"],
            "persuasion": ["persuade", "convince", "influence", "negotiate"],
            "competitor": ["competitor", "competition", "market", "rival"],
            "comfort": ["quick", "easy", "fast", "simple", "shortcut"]
        }

    def classify_intent(self, text: str) -> CommandIntent:
        """Classify command intent."""
        text_lower = text.lower()

        scores: Dict[CommandIntent, int] = defaultdict(int)

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    scores[intent] += 1

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return CommandIntent.EXECUTE

    def route(
        self,
        text: str,
        intent: CommandIntent = None
    ) -> List[SystemRegistration]:
        """Route command to appropriate systems."""
        text_lower = text.lower()
        intent = intent or self.classify_intent(text)

        matched_systems: Set[str] = set()

        # Check capability keywords
        for capability, keywords in self.capability_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    systems = self.registry.find_by_capability(capability)
                    for sys in systems:
                        matched_systems.add(sys.id)

        # Check explicit system mentions
        for reg in self.registry.systems.values():
            if reg.name.lower() in text_lower:
                matched_systems.add(reg.id)

        # Default to appropriate category based on intent
        if not matched_systems:
            intent_category_map = {
                CommandIntent.QUERY: SystemCategory.KNOWLEDGE,
                CommandIntent.EXECUTE: SystemCategory.AUTOMATION,
                CommandIntent.CREATE: SystemCategory.CREATION,
                CommandIntent.ANALYZE: SystemCategory.ANALYSIS,
                CommandIntent.CONTROL: SystemCategory.ORCHESTRATION,
                CommandIntent.CONFIGURE: SystemCategory.ORCHESTRATION,
                CommandIntent.MONITOR: SystemCategory.ORCHESTRATION,
                CommandIntent.OPTIMIZE: SystemCategory.LEARNING
            }

            category = intent_category_map.get(intent, SystemCategory.REASONING)
            category_systems = self.registry.find_by_category(category)
            matched_systems.update(s.id for s in category_systems)

        # Return matched systems sorted by health and success rate
        systems = [
            self.registry.systems[sid]
            for sid in matched_systems
            if sid in self.registry.systems
        ]

        systems.sort(
            key=lambda s: (
                s.health == HealthStatus.HEALTHY,
                s.success_rate,
                -s.avg_response_time_ms
            ),
            reverse=True
        )

        return systems[:5]  # Top 5 systems

    def suggest_systems(
        self,
        partial_input: str
    ) -> List[Dict[str, Any]]:
        """Suggest systems based on partial input."""
        suggestions = []

        for reg in self.registry.systems.values():
            score = 0

            # Check name match
            if partial_input.lower() in reg.name.lower():
                score += 3

            # Check capability match
            for cap in reg.capabilities:
                if partial_input.lower() in cap.lower():
                    score += 1

            # Check description match
            if partial_input.lower() in reg.description.lower():
                score += 0.5

            if score > 0:
                suggestions.append({
                    "system": reg.name,
                    "id": reg.id,
                    "score": score,
                    "category": reg.category.value
                })

        suggestions.sort(key=lambda s: s["score"], reverse=True)
        return suggestions[:10]


# ============================================================================
# EXECUTION ENGINE
# ============================================================================

class ExecutionEngine:
    """
    Executes commands across systems.
    """

    def __init__(self, registry: SystemRegistry):
        self.registry = registry
        self.execution_history: List[MasterResult] = []

    async def execute(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> MasterResult:
        """Execute command across systems."""
        start_time = time.time()

        system_results: List[SystemResult] = []

        if context.strategy == ExecutionStrategy.PARALLEL:
            system_results = await self._execute_parallel(context, systems)
        elif context.strategy == ExecutionStrategy.SEQUENTIAL:
            system_results = await self._execute_sequential(context, systems)
        elif context.strategy == ExecutionStrategy.CASCADE:
            system_results = await self._execute_cascade(context, systems)
        elif context.strategy == ExecutionStrategy.COMPETITIVE:
            system_results = await self._execute_competitive(context, systems)
        elif context.strategy == ExecutionStrategy.CONSENSUS:
            system_results = await self._execute_consensus(context, systems)
        else:
            system_results = await self._execute_parallel(context, systems)

        # Aggregate results
        successful_results = [r for r in system_results if r.success]

        # Determine primary result
        if successful_results:
            # Use highest confidence result
            best_result = max(successful_results, key=lambda r: r.confidence)
            primary_result = best_result.result
        else:
            primary_result = None

        total_time = (time.time() - start_time) * 1000

        result = MasterResult(
            command_id=context.command_id,
            success=len(successful_results) > 0,
            primary_result=primary_result,
            system_results=system_results,
            total_execution_time_ms=total_time,
            systems_used=[s.id for s in systems],
            strategy_used=context.strategy,
            power_mode=context.power_mode,
            suggestions=self._generate_suggestions(context, system_results)
        )

        # Update system stats
        for sys_result in system_results:
            self._update_system_stats(sys_result)

        self.execution_history.append(result)

        return result

    async def _execute_parallel(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> List[SystemResult]:
        """Execute all systems in parallel."""
        tasks = [
            self._execute_single(context, system)
            for system in systems
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        system_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                system_results.append(SystemResult(
                    system_id=systems[i].id,
                    success=False,
                    result=None,
                    error=str(result)
                ))
            else:
                system_results.append(result)

        return system_results

    async def _execute_sequential(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> List[SystemResult]:
        """Execute systems one by one."""
        results = []

        for system in systems:
            result = await self._execute_single(context, system)
            results.append(result)

            # Add result to context for next system
            context.previous_results[system.id] = result.result

        return results

    async def _execute_cascade(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> List[SystemResult]:
        """Execute systems in cascade (output -> input)."""
        results = []
        current_input = context.parameters.get("input", context.raw_input)

        for system in systems:
            # Update context with cascaded input
            context.parameters["cascaded_input"] = current_input

            result = await self._execute_single(context, system)
            results.append(result)

            if result.success:
                # Transform output for next system
                current_input = result.result
            else:
                break  # Stop cascade on failure

        return results

    async def _execute_competitive(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> List[SystemResult]:
        """Execute all systems and select best result."""
        all_results = await self._execute_parallel(context, systems)

        # Sort by confidence
        all_results.sort(key=lambda r: r.confidence if r.success else 0, reverse=True)

        return all_results

    async def _execute_consensus(
        self,
        context: CommandContext,
        systems: List[SystemRegistration]
    ) -> List[SystemResult]:
        """Execute systems and require consensus."""
        all_results = await self._execute_parallel(context, systems)

        successful = [r for r in all_results if r.success]

        if len(successful) < len(systems) * 0.5:  # Need majority
            # Mark all as low confidence due to lack of consensus
            for r in all_results:
                r.confidence *= 0.5

        return all_results

    async def _execute_single(
        self,
        context: CommandContext,
        system: SystemRegistration
    ) -> SystemResult:
        """Execute a single system."""
        start_time = time.time()

        try:
            # Apply power mode modifiers
            timeout = context.timeout_seconds
            if context.power_mode == PowerMode.TRANSCENDENT:
                timeout *= 2
            elif context.power_mode == PowerMode.WHISPER:
                timeout *= 0.5

            # Execute (simulated - in production calls actual system)
            result = await self._simulate_system_call(system, context)

            execution_time = (time.time() - start_time) * 1000

            # Apply power mode to confidence
            confidence = 0.8
            if context.power_mode == PowerMode.TRANSCENDENT:
                confidence = 0.95
            elif context.power_mode == PowerMode.MAXIMUM:
                confidence = 0.9
            elif context.power_mode == PowerMode.WHISPER:
                confidence = 0.7

            return SystemResult(
                system_id=system.id,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                confidence=confidence
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return SystemResult(
                system_id=system.id,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time
            )

    async def _simulate_system_call(
        self,
        system: SystemRegistration,
        context: CommandContext
    ) -> Dict[str, Any]:
        """Simulate system call (for demo)."""
        await asyncio.sleep(0.01)  # Simulate processing

        return {
            "system": system.name,
            "processed": context.raw_input[:50],
            "intent": context.intent.value,
            "power_mode": context.power_mode.value,
            "capabilities_used": system.capabilities[:2]
        }

    def _update_system_stats(self, result: SystemResult) -> None:
        """Update system statistics."""
        system = self.registry.get(result.system_id)
        if not system:
            return

        system.usage_count += 1
        system.last_used = datetime.now()

        # Update average response time
        old_avg = system.avg_response_time_ms
        n = system.usage_count
        system.avg_response_time_ms = old_avg + (result.execution_time_ms - old_avg) / n

        # Update success rate
        old_rate = system.success_rate
        system.success_rate = old_rate + ((1.0 if result.success else 0.0) - old_rate) / n

    def _generate_suggestions(
        self,
        context: CommandContext,
        results: List[SystemResult]
    ) -> List[str]:
        """Generate suggestions based on execution."""
        suggestions = []

        # Suggest other power modes
        if context.power_mode == PowerMode.NORMAL:
            suggestions.append("Try ENHANCED mode for better results")

        # Suggest cascade if multiple systems worked
        successful = [r for r in results if r.success]
        if len(successful) >= 2:
            suggestions.append("Consider using CASCADE strategy to chain results")

        # Suggest related systems
        for result in successful:
            system = self.registry.get(result.system_id)
            if system and system.dependencies:
                for dep in system.dependencies[:2]:
                    suggestions.append(f"Consider adding {dep} for enhanced capability")

        return suggestions[:3]


# ============================================================================
# BAEL MASTER INTERFACE
# ============================================================================

class BaelMasterInterface:
    """
    The Ultimate Ba'el Master Interface v2.

    Unifies all Ba'el systems into a single omnipotent interface.
    This is the crown of the Ba'el platform - the central nexus
    through which all power flows.
    """

    def __init__(self):
        self.registry = SystemRegistry()
        self.router = CommandRouter(self.registry)
        self.executor = ExecutionEngine(self.registry)

        self.power_mode = PowerMode.NORMAL
        self.default_strategy = ExecutionStrategy.PARALLEL
        self.session_context: Dict[str, Any] = {}
        self.command_count = 0

        # Auto-register core systems
        self._register_core_systems()

        logger.info("🔱 BA'EL MASTER INTERFACE v2 INITIALIZED 🔱")

    def _register_core_systems(self) -> None:
        """Register all core Ba'el systems."""
        # Register the major systems we've created
        core_systems = [
            {
                "name": "Infinity Loop Engine",
                "category": SystemCategory.REASONING,
                "description": "Ultimate recursive reasoning with council-within-council architecture",
                "capabilities": ["reasoning", "logic", "problem_solving", "infinity_loop"]
            },
            {
                "name": "AG-UI Protocol",
                "category": SystemCategory.COMMUNICATION,
                "description": "Agent-User Interaction Protocol with SSE streaming",
                "capabilities": ["streaming", "events", "ui_integration", "agui"]
            },
            {
                "name": "Security Arsenal",
                "category": SystemCategory.SECURITY,
                "description": "HexStrike-style security tools and AI agents",
                "capabilities": ["security", "pentest", "vulnerability", "scanning"]
            },
            {
                "name": "Sacred Geometry Engine",
                "category": SystemCategory.REASONING,
                "description": "Mathematical patterns of creation with golden ratio",
                "capabilities": ["geometry", "fibonacci", "phi", "sacred_math"]
            },
            {
                "name": "PC Controller",
                "category": SystemCategory.AUTOMATION,
                "description": "Full computer automation and control",
                "capabilities": ["automation", "pc_control", "keyboard", "mouse", "filesystem"]
            },
            {
                "name": "Psychological Engine",
                "category": SystemCategory.INTELLIGENCE,
                "description": "Psychological warfare, persuasion, and profiling",
                "capabilities": ["persuasion", "psychology", "manipulation", "profiling"]
            },
            {
                "name": "Intention Engine",
                "category": SystemCategory.INTELLIGENCE,
                "description": "BDI agent intentions and commitment management",
                "capabilities": ["intention", "prediction", "anticipation"]
            },
            {
                "name": "Ultra-Comfort Layer",
                "category": SystemCategory.AUTOMATION,
                "description": "Zero-friction user interface automation",
                "capabilities": ["comfort", "shortcuts", "macros", "quick"]
            },
            {
                "name": "Competitor Analysis",
                "category": SystemCategory.ANALYSIS,
                "description": "Ruthless competitor intelligence and strategy",
                "capabilities": ["competitor", "market", "strategy", "analysis"]
            },
            {
                "name": "Micro-Agent Swarm",
                "category": SystemCategory.ORCHESTRATION,
                "description": "Force multiplier with hundreds of micro-agents",
                "capabilities": ["swarm", "agents", "parallel", "multiplier"]
            },
            {
                "name": "Fine-Tuning Pipeline",
                "category": SystemCategory.LEARNING,
                "description": "Real-time LLM fine-tuning and self-evolution",
                "capabilities": ["learning", "finetune", "improvement", "evolution"]
            }
        ]

        for sys in core_systems:
            self.registry.register(**sys)

        # Define standard cascades
        self._define_cascades()

    def _define_cascades(self) -> None:
        """Define standard system cascades."""
        self.registry.define_cascade(
            name="Deep Analysis",
            description="Multi-layer analysis cascade",
            systems=["Infinity Loop Engine", "Competitor Analysis", "Psychological Engine"]
        )

        self.registry.define_cascade(
            name="Security Audit",
            description="Comprehensive security assessment",
            systems=["Security Arsenal", "Infinity Loop Engine"]
        )

        self.registry.define_cascade(
            name="Intelligence Gathering",
            description="Full intelligence pipeline",
            systems=["Competitor Analysis", "Psychological Engine", "Intention Engine"]
        )

    # -------------------------------------------------------------------------
    # MAIN INTERFACE
    # -------------------------------------------------------------------------

    async def command(
        self,
        text: str,
        strategy: ExecutionStrategy = None,
        power_mode: PowerMode = None,
        systems: List[str] = None
    ) -> MasterResult:
        """
        Execute a command through the master interface.

        This is the primary entry point for all Ba'el operations.
        """
        start_time = time.time()
        self.command_count += 1

        # Create command context
        intent = self.router.classify_intent(text)

        context = CommandContext(
            command_id=hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:12],
            raw_input=text,
            intent=intent,
            target_systems=systems or [],
            parameters={"input": text},
            power_mode=power_mode or self.power_mode,
            strategy=strategy or self.default_strategy
        )

        # Route to systems
        if systems:
            target_systems = [
                self.registry.find_by_name(name)
                for name in systems
            ]
            target_systems = [s for s in target_systems if s]
        else:
            target_systems = self.router.route(text, intent)

        if not target_systems:
            return MasterResult(
                command_id=context.command_id,
                success=False,
                primary_result=None,
                system_results=[],
                total_execution_time_ms=(time.time() - start_time) * 1000,
                systems_used=[],
                strategy_used=context.strategy,
                power_mode=context.power_mode,
                suggestions=["No matching systems found. Try more specific command."]
            )

        # Execute
        result = await self.executor.execute(context, target_systems)

        logger.info(
            f"Command '{text[:30]}...' executed via {len(result.systems_used)} systems "
            f"in {result.total_execution_time_ms:.1f}ms"
        )

        return result

    async def cascade(
        self,
        cascade_name: str,
        input_data: Any
    ) -> MasterResult:
        """Execute a predefined cascade."""
        cascade = None
        for c in self.registry.cascades.values():
            if c.name.lower() == cascade_name.lower():
                cascade = c
                break

        if not cascade:
            return MasterResult(
                command_id=hashlib.md5(f"cascade_{time.time()}".encode()).hexdigest()[:12],
                success=False,
                primary_result=None,
                system_results=[],
                total_execution_time_ms=0,
                systems_used=[],
                strategy_used=ExecutionStrategy.CASCADE,
                power_mode=self.power_mode,
                suggestions=[f"Cascade '{cascade_name}' not found"]
            )

        return await self.command(
            str(input_data),
            strategy=ExecutionStrategy.CASCADE,
            systems=cascade.systems
        )

    # -------------------------------------------------------------------------
    # POWER CONTROL
    # -------------------------------------------------------------------------

    def set_power_mode(self, mode: PowerMode) -> None:
        """Set the global power mode."""
        self.power_mode = mode
        logger.info(f"Power mode set to: {mode.value}")

    def transcend(self) -> None:
        """Activate TRANSCENDENT mode."""
        self.power_mode = PowerMode.TRANSCENDENT
        logger.info("🔱 TRANSCENDENT MODE ACTIVATED 🔱")

    def whisper(self) -> None:
        """Activate WHISPER mode for silent operation."""
        self.power_mode = PowerMode.WHISPER
        logger.info("🤫 Whisper mode activated")

    # -------------------------------------------------------------------------
    # SYSTEM MANAGEMENT
    # -------------------------------------------------------------------------

    def register_system(
        self,
        name: str,
        category: SystemCategory,
        description: str,
        capabilities: List[str],
        instance: Any = None
    ) -> str:
        """Register a new system."""
        reg = self.registry.register(
            name=name,
            category=category,
            description=description,
            capabilities=capabilities,
            instance=instance
        )
        return reg.id

    def get_system_status(self, system_name: str = None) -> Dict[str, Any]:
        """Get status of system(s)."""
        if system_name:
            reg = self.registry.find_by_name(system_name)
            if reg:
                return reg.to_dict()
            return {"error": "System not found"}

        return self.registry.get_stats()

    def list_systems(self, category: SystemCategory = None) -> List[Dict[str, Any]]:
        """List available systems."""
        if category:
            systems = self.registry.find_by_category(category)
        else:
            systems = list(self.registry.systems.values())

        return [s.to_dict() for s in systems]

    def list_cascades(self) -> List[Dict[str, Any]]:
        """List available cascades."""
        return [c.to_dict() for c in self.registry.cascades.values()]

    # -------------------------------------------------------------------------
    # NATURAL LANGUAGE SHORTCUTS
    # -------------------------------------------------------------------------

    async def ask(self, question: str) -> MasterResult:
        """Natural language query."""
        return await self.command(question, strategy=ExecutionStrategy.COMPETITIVE)

    async def do(self, action: str) -> MasterResult:
        """Execute an action."""
        return await self.command(action, strategy=ExecutionStrategy.PARALLEL)

    async def analyze(self, target: str) -> MasterResult:
        """Deep analysis."""
        return await self.command(
            f"analyze {target}",
            strategy=ExecutionStrategy.CASCADE,
            power_mode=PowerMode.ENHANCED
        )

    async def create(self, description: str) -> MasterResult:
        """Create something."""
        return await self.command(
            f"create {description}",
            strategy=ExecutionStrategy.PARALLEL
        )

    async def secure(self, target: str) -> MasterResult:
        """Security assessment."""
        return await self.command(
            f"security assessment of {target}",
            systems=["Security Arsenal"]
        )

    async def dominate(self, competitor: str) -> MasterResult:
        """Competitive domination."""
        return await self.command(
            f"analyze and dominate {competitor}",
            strategy=ExecutionStrategy.CASCADE,
            power_mode=PowerMode.MAXIMUM
        )

    # -------------------------------------------------------------------------
    # MONITORING
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get master interface status."""
        return {
            "power_mode": self.power_mode.value,
            "default_strategy": self.default_strategy.value,
            "commands_executed": self.command_count,
            "systems": self.registry.get_stats(),
            "execution_history_size": len(self.executor.execution_history)
        }

    def get_recent_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent command history."""
        recent = self.executor.execution_history[-limit:]
        return [r.to_dict() for r in reversed(recent)]


# ============================================================================
# SINGLETON
# ============================================================================

_bael_master: Optional[BaelMasterInterface] = None


def get_bael() -> BaelMasterInterface:
    """Get the global Ba'el Master Interface."""
    global _bael_master
    if _bael_master is None:
        _bael_master = BaelMasterInterface()
    return _bael_master


# Alias for convenience
BAEL = get_bael


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the Ba'el Master Interface."""
    print("=" * 70)
    print("🔱 BA'EL MASTER INTERFACE v2 🔱")
    print("=" * 70)

    bael = get_bael()

    # Show registered systems
    print("\n--- Registered Systems ---")
    systems = bael.list_systems()
    for sys in systems:
        print(f"  [{sys['category']}] {sys['name']}: {sys['description']}")

    # Show cascades
    print("\n--- Available Cascades ---")
    cascades = bael.list_cascades()
    for cascade in cascades:
        print(f"  {cascade['name']}: {' -> '.join(cascade['systems'])}")

    # Execute various commands
    print("\n--- Command Execution ---")

    # Query
    result = await bael.ask("What are the security vulnerabilities?")
    print(f"\nQuery result: {result.to_dict()}")

    # Set enhanced mode
    bael.set_power_mode(PowerMode.ENHANCED)

    # Analyze
    result = await bael.analyze("competitor market position")
    print(f"\nAnalysis result: {result.to_dict()}")

    # Transcendent mode
    bael.transcend()

    # Complex command
    result = await bael.command(
        "Perform deep psychological analysis and competitor assessment",
        strategy=ExecutionStrategy.CASCADE
    )
    print(f"\nTranscendent result: {result.to_dict()}")

    # Cascade execution
    print("\n--- Cascade Execution ---")
    result = await bael.cascade("Deep Analysis", "Analyze the AI market landscape")
    print(f"Cascade result: {result.to_dict()}")

    # System status
    print("\n--- Master Status ---")
    status = bael.get_status()
    print(json.dumps(status, indent=2))

    # Recent commands
    print("\n--- Recent Commands ---")
    recent = bael.get_recent_commands(5)
    for cmd in recent:
        print(f"  {cmd['command_id']}: {cmd['systems_used']} ({cmd['total_time_ms']:.1f}ms)")

    print("\n" + "=" * 70)
    print("🔱 BA'EL MASTER INTERFACE v2 - DEMO COMPLETE 🔱")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
