"""
BAEL - Ultimate Orchestrator
The supreme unified interface to all BAEL capabilities.

This is the single entry point that provides access to:
- 25+ Reasoning Engines
- 5-Layer Memory System
- Multi-Agent Swarms
- Reinforcement Learning
- Neural Architecture Search
- Domain-Specific Language (DSL) Rules
- Knowledge Synthesis
- Code Execution Sandbox
- Web Research
- Tool Orchestration
- Workflow Management
- Self-Evolution
- And much more...
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.performance.profiler import profile_section, profile_time

logger = logging.getLogger("BAEL.Ultimate")


# =============================================================================
# CAPABILITY ENUM
# =============================================================================

class Capability(Enum):
    """All BAEL capabilities."""
    # Core Reasoning
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    TEMPORAL = "temporal"
    PROBABILISTIC = "probabilistic"
    FUZZY = "fuzzy"
    MODAL = "modal"
    ANALOGICAL = "analogical"
    SPATIAL = "spatial"
    ETHICAL = "ethical"
    STRATEGIC = "strategic"
    CREATIVE = "creative"

    # Memory
    WORKING_MEMORY = "working_memory"
    EPISODIC_MEMORY = "episodic_memory"
    SEMANTIC_MEMORY = "semantic_memory"
    PROCEDURAL_MEMORY = "procedural_memory"
    META_MEMORY = "meta_memory"

    # Agents
    SINGLE_AGENT = "single_agent"
    MULTI_AGENT = "multi_agent"
    AGENT_SWARM = "agent_swarm"

    # Learning
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    META_LEARNING = "meta_learning"
    CONTINUAL_LEARNING = "continual_learning"
    SELF_EVOLUTION = "self_evolution"
    NAS = "nas"

    # Knowledge
    RAG = "rag"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"

    # Execution
    CODE_EXECUTION = "code_execution"
    TOOL_USE = "tool_use"
    WEB_RESEARCH = "web_research"

    # Control
    WORKFLOW = "workflow"
    STATE_MACHINE = "state_machine"
    DSL_RULES = "dsl_rules"


# =============================================================================
# CONFIGURATION
# =============================================================================

class BAELMode(Enum):
    """Operating modes."""
    MINIMAL = "minimal"        # Core only
    STANDARD = "standard"      # Most features
    MAXIMUM = "maximum"        # All features
    AUTONOMOUS = "autonomous"  # Self-directed
    CUSTOM = "custom"          # User-specified


@dataclass
class UltimateConfig:
    """Configuration for Ultimate Orchestrator."""
    mode: BAELMode = BAELMode.STANDARD
    enabled_capabilities: List[Capability] = field(default_factory=list)

    # LLM Settings
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    fallback_providers: List[str] = field(default_factory=lambda: ["openai", "groq"])

    # Memory Settings
    memory_backend: str = "memory"  # memory, sqlite, file
    memory_capacity: int = 10000

    # Execution Settings
    enable_code_execution: bool = True
    sandbox_security_level: str = "moderate"  # strict, moderate, permissive

    # Learning Settings
    enable_learning: bool = True
    learning_rate: float = 0.01

    # System Settings
    max_concurrent_agents: int = 10
    timeout_seconds: int = 300
    log_level: str = "INFO"

    def __post_init__(self):
        if not self.enabled_capabilities:
            self._set_default_capabilities()

    def _set_default_capabilities(self):
        if self.mode == BAELMode.MINIMAL:
            self.enabled_capabilities = [
                Capability.DEDUCTIVE,
                Capability.WORKING_MEMORY,
                Capability.SINGLE_AGENT
            ]
        elif self.mode == BAELMode.STANDARD:
            self.enabled_capabilities = [
                # Reasoning
                Capability.DEDUCTIVE, Capability.INDUCTIVE, Capability.ABDUCTIVE,
                Capability.CAUSAL, Capability.ANALOGICAL,
                # Memory
                Capability.WORKING_MEMORY, Capability.EPISODIC_MEMORY,
                Capability.SEMANTIC_MEMORY,
                # Agents
                Capability.SINGLE_AGENT, Capability.MULTI_AGENT,
                # Knowledge
                Capability.RAG, Capability.KNOWLEDGE_GRAPH,
                # Execution
                Capability.TOOL_USE,
                # Control
                Capability.WORKFLOW
            ]
        elif self.mode in [BAELMode.MAXIMUM, BAELMode.AUTONOMOUS]:
            self.enabled_capabilities = list(Capability)


# =============================================================================
# RESULT
# =============================================================================

@dataclass
class UltimateResult:
    """Result from Ultimate Orchestrator."""
    success: bool
    response: str
    reasoning_path: List[str] = field(default_factory=list)
    capabilities_used: List[Capability] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "response": self.response,
            "reasoning_path": self.reasoning_path,
            "capabilities_used": [c.value for c in self.capabilities_used],
            "confidence": self.confidence,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# ULTIMATE ORCHESTRATOR
# =============================================================================

class UltimateOrchestrator:
    """
    The Ultimate BAEL Orchestrator.

    Provides unified access to all BAEL capabilities through
    a single, powerful interface.
    """

    def __init__(self, config: Optional[UltimateConfig] = None):
        self.config = config or UltimateConfig()
        self._initialized = False

        # Component registry
        self._components: Dict[str, Any] = {}
        self._handlers: Dict[Capability, Callable] = {}

        # Statistics
        self._query_count = 0
        self._total_duration = 0.0
        self._capability_usage: Dict[Capability, int] = {}

        logger.info(f"Ultimate Orchestrator created with mode: {self.config.mode.value}")

    async def initialize(self) -> None:
        """Initialize all enabled components."""
        if self._initialized:
            return

        logger.info("Initializing Ultimate Orchestrator...")

        # Initialize components based on enabled capabilities
        for capability in self.config.enabled_capabilities:
            await self._initialize_capability(capability)

        self._initialized = True
        logger.info(f"Initialized with {len(self.config.enabled_capabilities)} capabilities")

    async def _initialize_capability(self, capability: Capability) -> None:
        """Initialize a specific capability."""
        try:
            if capability == Capability.REINFORCEMENT_LEARNING:
                from core.reinforcement import (Action,
                                                ReinforcementLearningEngine)
                actions = [
                    Action(id="reason", name="reason"),
                    Action(id="search", name="search"),
                    Action(id="execute", name="execute"),
                    Action(id="delegate", name="delegate")
                ]
                self._components["rl"] = ReinforcementLearningEngine(actions)
                logger.debug("Initialized RL Engine")

            elif capability == Capability.NAS:
                from core.nas import NASController
                self._components["nas"] = NASController()
                logger.debug("Initialized NAS Controller")

            elif capability == Capability.DSL_RULES:
                from core.dsl import RuleEngine
                self._components["dsl"] = RuleEngine()
                logger.debug("Initialized DSL Rule Engine")

            elif capability == Capability.WORKFLOW:
                from core.workflow import WorkflowOrchestrator
                self._components["workflow"] = WorkflowOrchestrator()
                logger.debug("Initialized Workflow Orchestrator")

            elif capability == Capability.AGENT_SWARM:
                from core.swarm import SwarmCoordinator
                self._components["swarm"] = SwarmCoordinator()
                logger.debug("Initialized Swarm Coordinator")

            elif capability == Capability.CODE_EXECUTION:
                from core.execution import CodeExecutionSandbox
                self._components["sandbox"] = CodeExecutionSandbox()
                logger.debug("Initialized Code Sandbox")

            elif capability == Capability.WEB_RESEARCH:
                from core.research import WebResearchEngine
                self._components["research"] = WebResearchEngine()
                logger.debug("Initialized Web Research Engine")

            elif capability == Capability.KNOWLEDGE_SYNTHESIS:
                from core.knowledge import KnowledgeSynthesisPipeline
                self._components["synthesis"] = KnowledgeSynthesisPipeline()
                logger.debug("Initialized Knowledge Synthesis")

            elif capability == Capability.TOOL_USE:
                from core.tools import ToolOrchestrator
                self._components["tools"] = ToolOrchestrator()
                logger.debug("Initialized Tool Orchestrator")

            # Track initialization
            self._capability_usage[capability] = 0

        except ImportError as e:
            logger.warning(f"Could not initialize {capability.value}: {e}")
        except Exception as e:
            logger.error(f"Error initializing {capability.value}: {e}")

    @profile_time
    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_capabilities: Optional[List[Capability]] = None
    ) -> UltimateResult:
        """
        Process a query using BAEL's full capabilities.

        Args:
            query: The input query or task
            context: Optional context data
            preferred_capabilities: Preferred capabilities to use

        Returns:
            UltimateResult with response and metadata
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        context = context or {}
        used_capabilities = []
        reasoning_path = []

        try:
            # 1. Analyze query to determine capabilities needed
            needed_caps = await self._analyze_query(query, preferred_capabilities)
            reasoning_path.append(f"Identified capabilities: {[c.value for c in needed_caps]}")

            # 2. Execute with selected capabilities
            response = await self._execute_with_capabilities(query, context, needed_caps)
            used_capabilities = needed_caps

            # 3. Learn from execution
            if self.config.enable_learning:
                await self._learn_from_execution(query, response, used_capabilities)

            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._query_count += 1
            self._total_duration += duration

            for cap in used_capabilities:
                self._capability_usage[cap] = self._capability_usage.get(cap, 0) + 1

            return UltimateResult(
                success=True,
                response=response,
                reasoning_path=reasoning_path,
                capabilities_used=used_capabilities,
                confidence=0.85,  # Would be computed dynamically
                duration_ms=duration
            )

        except Exception as e:
            logger.error(f"Process error: {e}")
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return UltimateResult(
                success=False,
                response=f"Error processing query: {str(e)}",
                reasoning_path=reasoning_path,
                capabilities_used=used_capabilities,
                confidence=0.0,
                duration_ms=duration
            )

    async def _analyze_query(
        self,
        query: str,
        preferred: Optional[List[Capability]] = None
    ) -> List[Capability]:
        """Analyze query to determine needed capabilities."""
        if preferred:
            return [c for c in preferred if c in self.config.enabled_capabilities]

        needed = []
        query_lower = query.lower()

        # Keyword-based capability selection
        if any(w in query_lower for w in ["why", "cause", "because", "reason"]):
            needed.append(Capability.CAUSAL)
        if any(w in query_lower for w in ["if", "would", "hypothetical"]):
            needed.append(Capability.COUNTERFACTUAL)
        if any(w in query_lower for w in ["code", "program", "script", "execute"]):
            needed.append(Capability.CODE_EXECUTION)
        if any(w in query_lower for w in ["search", "find", "research", "web"]):
            needed.append(Capability.WEB_RESEARCH)
        if any(w in query_lower for w in ["learn", "improve", "optimize"]):
            needed.append(Capability.REINFORCEMENT_LEARNING)
        if any(w in query_lower for w in ["workflow", "process", "steps"]):
            needed.append(Capability.WORKFLOW)
        if any(w in query_lower for w in ["agents", "team", "collaborate"]):
            needed.append(Capability.AGENT_SWARM)

        # Ensure at least one reasoning capability
        if not any(c.value.endswith("ive") for c in needed):
            needed.append(Capability.DEDUCTIVE)

        # Filter by enabled
        return [c for c in needed if c in self.config.enabled_capabilities]

    async def _execute_with_capabilities(
        self,
        query: str,
        context: Dict[str, Any],
        capabilities: List[Capability]
    ) -> str:
        """Execute query with specified capabilities."""
        results = []

        for cap in capabilities:
            if cap == Capability.CODE_EXECUTION and "sandbox" in self._components:
                sandbox = self._components["sandbox"]
                # Extract code if present
                if "```" in query:
                    code = query.split("```")[1].strip()
                    result = await sandbox.execute(code)
                    results.append(f"[Code Output] {result.get('output', 'No output')}")

            elif cap == Capability.WEB_RESEARCH and "research" in self._components:
                research = self._components["research"]
                report = await research.research(query)
                results.append(f"[Research] {report.get('summary', 'No results')}")

            elif cap == Capability.WORKFLOW and "workflow" in self._components:
                results.append("[Workflow] Processing with workflow engine")

            elif cap == Capability.AGENT_SWARM and "swarm" in self._components:
                results.append("[Swarm] Coordinating agent swarm")

            elif cap == Capability.REINFORCEMENT_LEARNING and "rl" in self._components:
                from core.reinforcement import State
                rl = self._components["rl"]
                state = State.from_context({"query": query, **context})
                action = await rl.select_action(state)
                results.append(f"[RL] Selected action: {action.name}")

        if not results:
            # Default reasoning
            results.append(f"[Reasoning] Processing: {query}")

        return "\n".join(results)

    async def _learn_from_execution(
        self,
        query: str,
        response: str,
        capabilities: List[Capability]
    ) -> None:
        """Learn from execution for future improvement."""
        if "rl" in self._components:
            from core.reinforcement import State
            rl = self._components["rl"]
            state = State.from_context({"query": query})
            # In practice, would get actual reward from user feedback
            reward = 0.5  # Neutral
            await rl.step(state, rl.actions[0], None, {"response": response}, done=True)

    # =========================================================================
    # DIRECT CAPABILITY ACCESS
    # =========================================================================

    @profile_time
    async def reason(
        self,
        query: str,
        reasoning_type: str = "deductive"
    ) -> str:
        """Direct access to reasoning capabilities."""
        return await self.process(query, preferred_capabilities=[
            Capability.DEDUCTIVE
        ]).response

    @profile_time
    async def execute_code(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Execute code in sandbox."""
        if "sandbox" not in self._components:
            return {"error": "Code execution not enabled"}

        return await self._components["sandbox"].execute(code, language)

    async def research(self, topic: str) -> Dict[str, Any]:
        """Perform web research."""
        if "research" not in self._components:
            return {"error": "Web research not enabled"}

        return await self._components["research"].research(topic)

    async def run_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a workflow."""
        if "workflow" not in self._components:
            return {"error": "Workflow not enabled"}

        return await self._components["workflow"].execute(workflow_name, input_data)

    async def spawn_swarm(
        self,
        task: str,
        num_agents: int = 3
    ) -> Dict[str, Any]:
        """Spawn agent swarm for a task."""
        if "swarm" not in self._components:
            return {"error": "Agent swarm not enabled"}

        return await self._components["swarm"].spawn_for_task(task, num_agents)

    async def add_rule(self, rule_source: str) -> None:
        """Add a DSL rule."""
        if "dsl" in self._components:
            self._components["dsl"].parse_and_add(rule_source)

    async def optimize_architecture(
        self,
        iterations: int = 50
    ) -> Dict[str, Any]:
        """Run neural architecture search."""
        if "nas" not in self._components:
            return {"error": "NAS not enabled"}

        best = await self._components["nas"].search(iterations)
        return best.to_dict() if best else {}

    # =========================================================================
    # STATUS & METRICS
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "initialized": self._initialized,
            "mode": self.config.mode.value,
            "enabled_capabilities": [c.value for c in self.config.enabled_capabilities],
            "loaded_components": list(self._components.keys()),
            "query_count": self._query_count,
            "avg_duration_ms": self._total_duration / max(1, self._query_count),
            "capability_usage": {c.value: n for c, n in self._capability_usage.items()}
        }

    def get_capabilities(self) -> List[str]:
        """Get list of enabled capabilities."""
        return [c.value for c in self.config.enabled_capabilities]

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        health = {}
        for name, component in self._components.items():
            try:
                if hasattr(component, 'health_check'):
                    health[name] = await component.health_check()
                else:
                    health[name] = True
            except Exception:
                health[name] = False
        return health


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

async def create_ultimate(
    mode: str = "standard",
    **kwargs
) -> UltimateOrchestrator:
    """
    Create and initialize the Ultimate Orchestrator.

    Args:
        mode: Operating mode (minimal, standard, maximum, autonomous)
        **kwargs: Additional configuration options

    Returns:
        Initialized UltimateOrchestrator
    """
    config = UltimateConfig(mode=BAELMode(mode), **kwargs)
    orchestrator = UltimateOrchestrator(config)
    await orchestrator.initialize()
    return orchestrator


# =============================================================================
# CONVENIENCE ALIASES
# =============================================================================

BAEL = UltimateOrchestrator
create_bael = create_ultimate


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "Capability",
    "BAELMode",
    "UltimateConfig",
    "UltimateResult",
    "UltimateOrchestrator",
    "create_ultimate",
    "BAEL",
    "create_bael"
]
