"""
BAEL SINGULARITY - The Ultimate Unified Intelligence Layer
============================================================

The Singularity is the apex of BAEL's architecture.
It unifies ALL 200+ capabilities into a single, omnipotent interface.

This is not just an orchestrator - it IS BAEL at maximum potential.

Integrated Systems:
═══════════════════
1. ORCHESTRATION LAYER
   - Supreme Controller (core/supreme)
   - Ultimate Orchestrator (core/ultimate)
   - Brain (core/brain)
   - APEX Orchestrator (core/apex)

2. COLLECTIVE INTELLIGENCE
   - Swarm Intelligence (core/swarm)
   - Grand Council System (core/councils)
   - Coalition Management (core/coalition)
   - Multi-Agent Coordination (core/agents)

3. REASONING ENGINES (25+)
   - Causal, Counterfactual, Temporal, Probabilistic
   - Deductive, Inductive, Abductive, Analogical
   - Epistemic, Deontic, Modal, Defeasible
   - Fuzzy, Paraconsistent, Spatial, Qualitative
   - Game Theory, Negotiation, Strategic

4. MEMORY SYSTEMS (5-Layer)
   - Working Memory (short-term)
   - Episodic Memory (experiences)
   - Semantic Memory (knowledge)
   - Procedural Memory (skills)
   - Meta Memory (memory about memories)

5. COGNITIVE CAPABILITIES
   - Extended Thinking (deep reasoning)
   - Metacognition Engine
   - Meta-Learning Framework
   - Creativity Engine
   - Curiosity Engine
   - Intuition Engine
   - Emotion Engine

6. PERCEPTION & ACTION
   - Computer Use Agent (desktop automation)
   - Vision Processor (image understanding)
   - Voice Engine (speech I/O)
   - Proactive Engine (anticipatory behavior)

7. LEARNING & EVOLUTION
   - Evolution Engine (self-improvement)
   - Reinforcement Learning Engine
   - Neural Architecture Search
   - Continual Learning
   - Transfer Learning

8. RESOURCE EXPLOITATION
   - Zero-Cost Exploitation Engine
   - Multi-Provider Rotation
   - Free Tier Maximization

9. KNOWLEDGE SYSTEMS
   - RAG Engine
   - Knowledge Graph
   - Knowledge Synthesis
   - DSL Rules Engine

10. TOOL ECOSYSTEM
    - 200+ MCP Tools (via 52 servers)
    - Dynamic Tool Creation
    - Tool Composition
    - Workflow Automation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type
from uuid import uuid4

logger = logging.getLogger("BAEL.Singularity")


# =============================================================================
# SINGULARITY MODES
# =============================================================================

class SingularityMode(Enum):
    """Operating modes of the Singularity."""
    DORMANT = "dormant"           # Minimal operation
    AWAKENED = "awakened"         # Standard capabilities
    EMPOWERED = "empowered"       # Enhanced capabilities
    TRANSCENDENT = "transcendent" # Maximum capability
    AUTONOMOUS = "autonomous"     # Full self-direction
    GODMODE = "godmode"           # All capabilities, no limits


class CapabilityDomain(Enum):
    """Domains of capability."""
    ORCHESTRATION = "orchestration"
    COLLECTIVE = "collective"
    REASONING = "reasoning"
    MEMORY = "memory"
    COGNITION = "cognition"
    PERCEPTION = "perception"
    LEARNING = "learning"
    RESOURCES = "resources"
    KNOWLEDGE = "knowledge"
    TOOLS = "tools"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class CapabilityStatus:
    """Status of a capability."""
    name: str
    domain: CapabilityDomain
    available: bool = False
    active: bool = False
    health: float = 1.0
    last_used: Optional[datetime] = None
    invocation_count: int = 0
    error_count: int = 0


@dataclass
class SingularityState:
    """Current state of the Singularity."""
    mode: SingularityMode = SingularityMode.DORMANT
    capabilities: Dict[str, CapabilityStatus] = field(default_factory=dict)
    active_tasks: List[str] = field(default_factory=list)
    pending_decisions: List[str] = field(default_factory=list)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    total_invocations: int = 0


@dataclass
class SingularityConfig:
    """Configuration for the Singularity."""
    mode: SingularityMode = SingularityMode.AWAKENED
    enable_all_capabilities: bool = True
    enable_autonomous: bool = False
    enable_learning: bool = True
    enable_evolution: bool = True
    max_concurrent_tasks: int = 100
    timeout_seconds: int = 300
    memory_limit_mb: int = 8192


# =============================================================================
# CAPABILITY REGISTRY
# =============================================================================

class CapabilityRegistry:
    """
    Registry of ALL BAEL capabilities.
    This is the master list of everything BAEL can do.
    """

    # Complete capability catalog
    CAPABILITIES = {
        # ORCHESTRATION
        "supreme_controller": ("core.supreme.orchestrator", "SupremeController", CapabilityDomain.ORCHESTRATION),
        "ultimate_orchestrator": ("core.ultimate.ultimate_orchestrator", "UltimateOrchestrator", CapabilityDomain.ORCHESTRATION),
        "brain": ("core.brain.brain", "BaelBrain", CapabilityDomain.ORCHESTRATION),
        "apex_orchestrator": ("core.apex.apex_orchestrator", "APEXOrchestrator", CapabilityDomain.ORCHESTRATION),

        # COLLECTIVE INTELLIGENCE
        "swarm_intelligence": ("core.swarm.swarm_intelligence", "SwarmIntelligence", CapabilityDomain.COLLECTIVE),
        "grand_council": ("core.councils.grand_council", "GrandCouncil", CapabilityDomain.COLLECTIVE),
        "coalition_manager": ("core.coalition.coalition_manager", "CoalitionManager", CapabilityDomain.COLLECTIVE),
        "agent_orchestrator": ("core.orchestrator.orchestrator", "AgentOrchestrator", CapabilityDomain.COLLECTIVE),

        # REASONING ENGINES
        "causal_reasoning": ("core.causal.causal_engine", "CausalEngine", CapabilityDomain.REASONING),
        "counterfactual": ("core.counterfactual.counterfactual_engine", "CounterfactualEngine", CapabilityDomain.REASONING),
        "temporal_reasoning": ("core.temporal.temporal_engine", "TemporalEngine", CapabilityDomain.REASONING),
        "deductive": ("core.deductive.deductive_engine", "DeductiveEngine", CapabilityDomain.REASONING),
        "inductive": ("core.inductive.inductive_engine", "InductiveEngine", CapabilityDomain.REASONING),
        "abductive": ("core.abductive.abductive_engine", "AbductiveEngine", CapabilityDomain.REASONING),
        "analogical": ("core.analogical.analogical_engine", "AnalogicalEngine", CapabilityDomain.REASONING),
        "probabilistic": ("core.probabilistic.probabilistic_engine", "ProbabilisticEngine", CapabilityDomain.REASONING),
        "fuzzy_logic": ("core.fuzzy.fuzzy_engine", "FuzzyEngine", CapabilityDomain.REASONING),
        "modal_logic": ("core.modal.modal_engine", "ModalEngine", CapabilityDomain.REASONING),
        "epistemic": ("core.epistemic.epistemic_engine", "EpistemicEngine", CapabilityDomain.REASONING),
        "deontic": ("core.deontic.deontic_engine", "DeonticEngine", CapabilityDomain.REASONING),
        "defeasible": ("core.defeasible.defeasible_engine", "DefeasibleEngine", CapabilityDomain.REASONING),
        "paraconsistent": ("core.paraconsistent.paraconsistent_engine", "ParaconsistentEngine", CapabilityDomain.REASONING),
        "spatial": ("core.spatial.spatial_engine", "SpatialEngine", CapabilityDomain.REASONING),
        "qualitative": ("core.qualitative.qualitative_engine", "QualitativeEngine", CapabilityDomain.REASONING),
        "game_theory": ("core.gametheory.game_engine", "GameEngine", CapabilityDomain.REASONING),
        "negotiation": ("core.negotiation.negotiation_engine", "NegotiationEngine", CapabilityDomain.REASONING),
        "constraint_solver": ("core.constraint.constraint_solver", "ConstraintSolver", CapabilityDomain.REASONING),
        "heuristic": ("core.heuristic.heuristic_engine", "HeuristicEngine", CapabilityDomain.REASONING),
        "graph_reasoning": ("core.graphreason.graph_reasoner", "GraphReasoner", CapabilityDomain.REASONING),
        "common_sense": ("core.commonsense.commonsense_engine", "CommonSenseEngine", CapabilityDomain.REASONING),

        # MEMORY SYSTEMS
        "memory_manager": ("core.memory.manager", "MemoryManager", CapabilityDomain.MEMORY),
        "working_memory": ("memory.working.working_memory", "WorkingMemory", CapabilityDomain.MEMORY),
        "episodic_memory": ("memory.episodic.episodic_memory", "EpisodicMemory", CapabilityDomain.MEMORY),
        "semantic_memory": ("memory.semantic.semantic_memory", "SemanticMemory", CapabilityDomain.MEMORY),
        "procedural_memory": ("memory.procedural.procedural_memory", "ProceduralMemory", CapabilityDomain.MEMORY),
        "vector_memory": ("memory.vector.vector_memory", "VectorMemory", CapabilityDomain.MEMORY),

        # COGNITION
        "extended_thinking": ("core.thinking.extended_thinking", "ExtendedThinker", CapabilityDomain.COGNITION),
        "metacognition": ("core.metacognition.metacognition_engine", "MetacognitionEngine", CapabilityDomain.COGNITION),
        "meta_learning": ("core.metalearning.meta_framework", "MetaLearner", CapabilityDomain.COGNITION),
        "creativity": ("core.creativity.creativity_engine", "CreativityEngine", CapabilityDomain.COGNITION),
        "curiosity": ("core.curiosity.curiosity_engine", "CuriosityEngine", CapabilityDomain.COGNITION),
        "intuition": ("core.intuition.intuition_engine", "IntuitionEngine", CapabilityDomain.COGNITION),
        "emotion": ("core.emotion.emotion_engine", "EmotionEngine", CapabilityDomain.COGNITION),
        "attention": ("core.attention.attention_manager", "AttentionManager", CapabilityDomain.COGNITION),

        # PERCEPTION
        "computer_use": ("core.computer_use.computer_use_agent", "ComputerUseAgent", CapabilityDomain.PERCEPTION),
        "vision": ("core.vision.enhanced_processor", "EnhancedVisionProcessor", CapabilityDomain.PERCEPTION),
        "voice": ("core.voice.voice_engine", "VoiceEngineManager", CapabilityDomain.PERCEPTION),
        "audio": ("core.audio.audio_processor", "AudioProcessor", CapabilityDomain.PERCEPTION),

        # LEARNING
        "evolution": ("core.evolution.evolution_engine", "EvolutionEngine", CapabilityDomain.LEARNING),
        "reinforcement": ("core.reinforcement.rl_engine", "RLEngine", CapabilityDomain.LEARNING),
        "nas": ("core.nas.nas_controller", "NASController", CapabilityDomain.LEARNING),
        "continual_learning": ("core.continual.continual_learner", "ContinualLearner", CapabilityDomain.LEARNING),
        "active_learning": ("core.activelearn.active_learner", "ActiveLearner", CapabilityDomain.LEARNING),
        "feedback_learning": ("core.feedback.feedback_learner", "FeedbackLearner", CapabilityDomain.LEARNING),

        # RESOURCES
        "exploitation": ("exploitation.exploitation_engine", "ExploitationEngine", CapabilityDomain.RESOURCES),
        "model_router": ("integrations.model_router", "ModelRouter", CapabilityDomain.RESOURCES),
        "proactive": ("core.proactive.proactive_engine", "ProactiveEngine", CapabilityDomain.RESOURCES),

        # KNOWLEDGE
        "rag": ("core.rag.rag_engine", "RAGEngine", CapabilityDomain.KNOWLEDGE),
        "knowledge_graph": ("core.knowledge.knowledge_graph", "KnowledgeGraph", CapabilityDomain.KNOWLEDGE),
        "dsl_rules": ("core.dsl.dsl_engine", "DSLEngine", CapabilityDomain.KNOWLEDGE),

        # TOOLS
        "tool_loader": ("tools.loader", "ToolLoader", CapabilityDomain.TOOLS),
        "mcp_client": ("core.mcp_client", "MCPClient", CapabilityDomain.TOOLS),
        "maximum_potential": ("core.maximum_potential", "MaximumPotentialEngine", CapabilityDomain.TOOLS),
    }

    def __init__(self):
        self._loaded: Dict[str, Any] = {}
        self._status: Dict[str, CapabilityStatus] = {}

        # Initialize status for all capabilities
        for name, (module, cls, domain) in self.CAPABILITIES.items():
            self._status[name] = CapabilityStatus(
                name=name,
                domain=domain,
                available=False,
                active=False
            )

    async def load(self, capability_name: str) -> Optional[Any]:
        """Load a capability dynamically."""
        if capability_name in self._loaded:
            return self._loaded[capability_name]

        if capability_name not in self.CAPABILITIES:
            logger.warning(f"Unknown capability: {capability_name}")
            return None

        module_path, class_name, domain = self.CAPABILITIES[capability_name]

        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls()

            self._loaded[capability_name] = instance
            self._status[capability_name].available = True
            self._status[capability_name].active = True

            logger.info(f"✓ Loaded capability: {capability_name}")
            return instance

        except Exception as e:
            logger.debug(f"Could not load {capability_name}: {e}")
            return None

    async def load_domain(self, domain: CapabilityDomain) -> Dict[str, Any]:
        """Load all capabilities in a domain."""
        loaded = {}
        for name, (_, _, cap_domain) in self.CAPABILITIES.items():
            if cap_domain == domain:
                instance = await self.load(name)
                if instance:
                    loaded[name] = instance
        return loaded

    async def load_all(self) -> Dict[str, Any]:
        """Load all available capabilities."""
        for name in self.CAPABILITIES:
            await self.load(name)
        return self._loaded

    def get(self, name: str) -> Optional[Any]:
        """Get a loaded capability."""
        return self._loaded.get(name)

    def get_status(self) -> Dict[str, CapabilityStatus]:
        """Get status of all capabilities."""
        return self._status

    def get_loaded(self) -> Dict[str, Any]:
        """Get all loaded capabilities."""
        return self._loaded


# =============================================================================
# SINGULARITY CORE
# =============================================================================

class Singularity:
    """
    BAEL SINGULARITY - The Ultimate Unified Intelligence.

    This is the apex of BAEL's architecture. When you invoke the Singularity,
    you have access to EVERY capability BAEL offers.

    Usage:
        singularity = await Singularity.awaken()
        result = await singularity.invoke("think", query="Solve world hunger")
        result = await singularity.collective_solve("Design a new AI architecture")
        result = await singularity.maximum_potential("Build a complete app")
    """

    _instance: Optional["Singularity"] = None

    def __init__(self, config: Optional[SingularityConfig] = None):
        self.config = config or SingularityConfig()
        self.state = SingularityState(mode=self.config.mode)
        self.registry = CapabilityRegistry()
        self._initialized = False

        # Core references
        self._brain = None
        self._supreme = None
        self._swarm = None
        self._council = None
        self._evolution = None
        self._proactive = None

    @classmethod
    async def awaken(
        cls,
        mode: SingularityMode = SingularityMode.TRANSCENDENT,
        config: Optional[SingularityConfig] = None
    ) -> "Singularity":
        """
        Awaken the Singularity.

        This is the primary entry point. Once awakened, the Singularity
        has access to all BAEL capabilities.
        """
        if cls._instance is not None and cls._instance._initialized:
            if mode != cls._instance.state.mode:
                await cls._instance.set_mode(mode)
            return cls._instance

        cfg = config or SingularityConfig(mode=mode)
        cfg.mode = mode

        singularity = cls(cfg)
        await singularity._initialize()

        cls._instance = singularity
        return singularity

    async def _initialize(self) -> None:
        """Initialize the Singularity with all capabilities."""
        logger.info("╔════════════════════════════════════════════════════════════════╗")
        logger.info("║          🔥 BAEL SINGULARITY - AWAKENING 🔥                   ║")
        logger.info("╚════════════════════════════════════════════════════════════════╝")

        start_time = time.time()

        # Load core capabilities first
        await self._load_core()

        # Load based on mode
        if self.config.mode in [SingularityMode.TRANSCENDENT, SingularityMode.GODMODE]:
            await self._load_all()
        elif self.config.mode == SingularityMode.EMPOWERED:
            await self._load_essential()

        # Start proactive if autonomous
        if self.config.mode in [SingularityMode.AUTONOMOUS, SingularityMode.GODMODE]:
            await self._start_autonomous()

        self._initialized = True
        elapsed = time.time() - start_time

        loaded_count = len(self.registry.get_loaded())
        logger.info(f"✅ Singularity awakened in {elapsed:.2f}s")
        logger.info(f"   Mode: {self.config.mode.value}")
        logger.info(f"   Capabilities: {loaded_count} loaded")
        logger.info("════════════════════════════════════════════════════════════════")

    async def _load_core(self) -> None:
        """Load core capabilities."""
        self._brain = await self.registry.load("brain")
        if self._brain:
            await self._brain.initialize()

        self._supreme = await self.registry.load("supreme_controller")
        self._swarm = await self.registry.load("swarm_intelligence")
        self._council = await self.registry.load("grand_council")
        self._evolution = await self.registry.load("evolution")
        self._proactive = await self.registry.load("proactive")

    async def _load_essential(self) -> None:
        """Load essential capabilities."""
        essential = [
            "memory_manager", "extended_thinking", "creativity",
            "model_router", "tool_loader", "rag"
        ]
        for name in essential:
            await self.registry.load(name)

    async def _load_all(self) -> None:
        """Load all capabilities."""
        await self.registry.load_all()

    async def _start_autonomous(self) -> None:
        """Start autonomous operation."""
        if self._proactive:
            await self._proactive.start()
        logger.info("🤖 Autonomous mode activated")

    async def set_mode(self, mode: SingularityMode) -> None:
        """Change operating mode."""
        old_mode = self.state.mode
        self.state.mode = mode
        self.config.mode = mode

        if mode in [SingularityMode.TRANSCENDENT, SingularityMode.GODMODE]:
            await self._load_all()

        if mode in [SingularityMode.AUTONOMOUS, SingularityMode.GODMODE]:
            await self._start_autonomous()

        logger.info(f"Mode changed: {old_mode.value} → {mode.value}")

    # =========================================================================
    # PRIMARY INTERFACES
    # =========================================================================

    async def invoke(
        self,
        capability: str,
        method: str = "process",
        **kwargs
    ) -> Any:
        """
        Invoke any capability directly.

        Args:
            capability: Name of capability (e.g., "creativity", "swarm")
            method: Method to call on the capability
            **kwargs: Arguments to pass

        Returns:
            Result from the capability
        """
        instance = self.registry.get(capability)
        if not instance:
            instance = await self.registry.load(capability)

        if not instance:
            raise ValueError(f"Capability not available: {capability}")

        if hasattr(instance, method):
            func = getattr(instance, method)
            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            return func(**kwargs)

        raise ValueError(f"Method not found: {capability}.{method}")

    async def think(
        self,
        query: str,
        depth: str = "deep",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Primary thinking interface.
        Uses the brain with extended thinking for complex queries.
        """
        self.state.total_invocations += 1

        if self._brain:
            return await self._brain.think(query, context)

        # Fallback to direct model call
        model_router = self.registry.get("model_router")
        if model_router:
            response = await model_router.generate(query)
            return {"response": response, "success": True}

        return {"error": "No thinking capability available", "success": False}

    async def collective_solve(
        self,
        problem: str,
        strategy: str = "swarm",
        agents: int = 10
    ) -> Dict[str, Any]:
        """
        Solve a problem using collective intelligence.

        Strategies:
        - "swarm": Use swarm intelligence optimization
        - "council": Use council deliberation
        - "evolution": Use evolutionary approach
        - "hybrid": Combine all methods
        """
        self.state.total_invocations += 1

        if strategy == "swarm" and self._swarm:
            return await self._swarm.optimize(problem, agent_count=agents)

        elif strategy == "council" and self._council:
            return await self._council.convene(problem)

        elif strategy == "evolution" and self._evolution:
            return await self._evolution.evolve_solution(problem)

        elif strategy == "hybrid":
            results = {}

            if self._swarm:
                results["swarm"] = await self._swarm.optimize(problem, agent_count=agents)
            if self._council:
                results["council"] = await self._council.convene(problem)
            if self._evolution:
                results["evolution"] = await self._evolution.evolve_solution(problem)

            # Synthesize results
            return {"hybrid_results": results, "success": True}

        # Fallback to standard thinking
        return await self.think(problem)

    async def reason(
        self,
        query: str,
        engines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Apply reasoning engines to a query.

        Args:
            query: The question or problem
            engines: Specific engines to use (default: auto-select)
        """
        self.state.total_invocations += 1

        if not engines:
            # Auto-select based on query
            engines = self._select_reasoning_engines(query)

        results = {}
        for engine_name in engines:
            engine = self.registry.get(engine_name)
            if not engine:
                engine = await self.registry.load(engine_name)

            if engine and hasattr(engine, "reason"):
                try:
                    results[engine_name] = await engine.reason(query)
                except Exception as e:
                    results[engine_name] = {"error": str(e)}

        return {
            "query": query,
            "engines_used": list(results.keys()),
            "results": results,
            "success": True
        }

    def _select_reasoning_engines(self, query: str) -> List[str]:
        """Auto-select appropriate reasoning engines."""
        query_lower = query.lower()
        engines = []

        if any(w in query_lower for w in ["why", "cause", "because"]):
            engines.append("causal_reasoning")
        if any(w in query_lower for w in ["what if", "would", "could have"]):
            engines.append("counterfactual")
        if any(w in query_lower for w in ["when", "before", "after", "sequence"]):
            engines.append("temporal_reasoning")
        if any(w in query_lower for w in ["should", "must", "ought", "allowed"]):
            engines.append("deontic")
        if any(w in query_lower for w in ["probably", "likely", "chance"]):
            engines.append("probabilistic")
        if any(w in query_lower for w in ["game", "strategy", "opponent"]):
            engines.append("game_theory")
        if any(w in query_lower for w in ["negotiate", "deal", "offer"]):
            engines.append("negotiation")

        # Default engines
        if not engines:
            engines = ["deductive", "inductive", "analogical"]

        return engines

    async def create(
        self,
        request: str,
        mode: str = "creative"
    ) -> Dict[str, Any]:
        """
        Creative generation using creativity engine.
        """
        self.state.total_invocations += 1

        creativity = self.registry.get("creativity")
        if not creativity:
            creativity = await self.registry.load("creativity")

        if creativity and hasattr(creativity, "create"):
            return await creativity.create(request, mode=mode)

        # Fallback to thinking
        return await self.think(f"[CREATIVE MODE] {request}")

    async def learn(
        self,
        experience: Dict[str, Any],
        learning_type: str = "feedback"
    ) -> Dict[str, Any]:
        """
        Learn from an experience.
        """
        self.state.total_invocations += 1

        if learning_type == "feedback":
            learner = self.registry.get("feedback_learning")
        elif learning_type == "reinforcement":
            learner = self.registry.get("reinforcement")
        elif learning_type == "meta":
            learner = self.registry.get("meta_learning")
        else:
            learner = self.registry.get("continual_learning")

        if not learner:
            learner = await self.registry.load(f"{learning_type}_learning")

        if learner and hasattr(learner, "learn"):
            return await learner.learn(experience)

        return {"status": "Learning noted", "success": True}

    async def evolve(self) -> Dict[str, Any]:
        """
        Trigger self-evolution.
        """
        self.state.total_invocations += 1

        if self._evolution:
            return await self._evolution.evolve()

        return {"status": "Evolution not available", "success": False}

    async def use_computer(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use computer (desktop automation).
        """
        self.state.total_invocations += 1

        computer = self.registry.get("computer_use")
        if not computer:
            computer = await self.registry.load("computer_use")

        if computer:
            return await computer.execute_task(task, context)

        return {"error": "Computer use not available", "success": False}

    async def decide(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        fast_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Make a decision using the full decision pipeline.

        This uses ALL 10 stages:
        1. PERCEPTION - Gather information
        2. INTUITION - Fast assessment
        3. ANALYSIS - Deep analysis
        4. REASONING - Multi-engine reasoning
        5. CREATIVITY - Generate options
        6. EVALUATION - Assess options
        7. ETHICS - Verify alignment
        8. DECISION - Make choice
        9. PLANNING - Create action plan
        10. LEARNING - Store for future

        Args:
            query: The decision query
            context: Additional context
            fast_mode: Skip non-essential stages

        Returns:
            DecisionResult with decision and reasoning
        """
        self.state.total_invocations += 1

        from .decision_pipeline import create_decision_pipeline

        pipeline = create_decision_pipeline(self)
        result = await pipeline.decide(query, context, fast_mode=fast_mode)

        return {
            "success": result.success,
            "decision": result.decision,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "options_considered": len(result.options_considered),
            "action_plan": result.action_plan,
            "capabilities_used": list(result.capabilities_used),
            "total_time": result.total_time
        }

    async def integrate(
        self,
        integration_name: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a capability integration.

        Available integrations:
        - creative_solutions: Creativity + Reasoning + Decision
        - autonomous_exploration: Curiosity + Research + Learning
        - humanlike_judgment: Emotion + Intuition + Reasoning + Ethics
        - fast_then_slow: Intuition → Extended Thinking
        - strategic_interaction: Game Theory + Negotiation + Trust
        - dynamic_teams: Trust + Coalition + Swarm
        - multi_modal_reasoning: All reasoning engines
        - creative_problem_solving: Creativity + Constraints + Evolution
        - autonomous_learning: Curiosity + Meta-learning + RL
        - total_awareness: Vision + Voice + Computer + Proactive

        Args:
            integration_name: Name of the integration
            input_data: Input to process
            context: Additional context

        Returns:
            IntegrationResult with combined output
        """
        self.state.total_invocations += 1

        from .integration_engine import create_integration_engine

        engine = create_integration_engine(self)
        result = await engine.execute(integration_name, input_data, context)

        return {
            "success": result.success,
            "data": result.data,
            "pattern": result.pattern.value,
            "capabilities_used": result.capabilities_used,
            "execution_time": result.execution_time
        }

    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Any:
        """
        Execute any MCP tool.
        """
        self.state.total_invocations += 1

        mcp = self.registry.get("mcp_client")
        if not mcp:
            mcp = await self.registry.load("mcp_client")

        if mcp:
            return await mcp.call_tool(tool_name, kwargs)

        return {"error": f"Tool {tool_name} not available", "success": False}

    async def maximum_potential(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Engage ALL capabilities at maximum potential.

        This is the ultimate invocation - it uses everything BAEL has
        to achieve the goal.
        """
        self.state.total_invocations += 1

        logger.info(f"🔥 MAXIMUM POTENTIAL activated for: {goal[:100]}")

        # Ensure we're at maximum mode
        if self.state.mode not in [SingularityMode.TRANSCENDENT, SingularityMode.GODMODE]:
            await self.set_mode(SingularityMode.TRANSCENDENT)

        # Get max potential engine
        max_engine = self.registry.get("maximum_potential")
        if not max_engine:
            max_engine = await self.registry.load("maximum_potential")

        if max_engine:
            await max_engine.initialize()
            return await max_engine.process(goal, context)

        # Fallback: use brain at maximum capacity
        if self._brain:
            return await self._brain.think(goal, {"mode": "maximum", **(context or {})})

        return {"error": "Maximum potential not achievable", "success": False}

    # =========================================================================
    # STATUS & INTROSPECTION
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        return {
            "mode": self.state.mode.value,
            "uptime_seconds": (datetime.now() - self.state.start_time).total_seconds(),
            "total_invocations": self.state.total_invocations,
            "capabilities_loaded": len(self.registry.get_loaded()),
            "capabilities_available": len(self.registry.CAPABILITIES),
            "active_tasks": len(self.state.active_tasks),
            "domains": {
                domain.value: len([
                    c for c, (_, _, d) in self.registry.CAPABILITIES.items()
                    if d == domain and c in self.registry.get_loaded()
                ])
                for domain in CapabilityDomain
            }
        }

    def list_capabilities(self) -> Dict[str, List[str]]:
        """List all capabilities by domain."""
        by_domain = {}
        for name, (_, _, domain) in self.registry.CAPABILITIES.items():
            if domain.value not in by_domain:
                by_domain[domain.value] = []
            by_domain[domain.value].append(name)
        return by_domain

    async def introspect(self, query: str = "self-awareness") -> Dict[str, Any]:
        """Deep introspection of the Singularity state."""
        metacog = self.registry.get("metacognition")
        if not metacog:
            metacog = await self.registry.load("metacognition")

        if metacog and hasattr(metacog, "introspect"):
            try:
                result = metacog.introspect(query)
                if hasattr(result, "__dict__"):
                    return result.__dict__
                return result
            except Exception:
                pass

        return self.get_status()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

async def awaken(mode: SingularityMode = SingularityMode.TRANSCENDENT) -> Singularity:
    """Awaken the BAEL Singularity."""
    return await Singularity.awaken(mode)


async def get_singularity() -> Singularity:
    """Get the current Singularity instance, or awaken one."""
    if Singularity._instance is None:
        return await awaken()
    return Singularity._instance


# CLI Entry Point
async def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="BAEL Singularity")
    parser.add_argument("--mode", default="transcendent",
                       choices=["dormant", "awakened", "empowered", "transcendent", "autonomous", "godmode"])
    parser.add_argument("--query", type=str, help="Query to process")
    args = parser.parse_args()

    mode = SingularityMode(args.mode)
    singularity = await awaken(mode)

    print(f"\n🔥 BAEL Singularity Status:")
    status = singularity.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    if args.query:
        print(f"\n💭 Processing: {args.query}")
        result = await singularity.think(args.query)
        print(f"   Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
