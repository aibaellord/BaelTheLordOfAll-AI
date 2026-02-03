"""
BAEL SINGULARITY API - Complete Unified Capability Access
==========================================================

This API provides HTTP access to EVERY BAEL capability through
a single unified interface. It's the crown jewel of BAEL's API layer.

Endpoints:
- POST /singularity/awaken - Awaken the singularity
- POST /singularity/think - Primary thinking interface
- POST /singularity/collective - Collective problem solving
- POST /singularity/reason - Multi-engine reasoning
- POST /singularity/create - Creative generation
- POST /singularity/learn - Learning interface
- POST /singularity/evolve - Trigger evolution
- POST /singularity/computer - Desktop automation
- POST /singularity/tool - Execute MCP tools
- POST /singularity/maximum - Maximum potential mode
- POST /singularity/invoke - Invoke any capability
- GET /singularity/status - Get current status
- GET /singularity/capabilities - List all capabilities
- GET /singularity/introspect - Deep introspection

Additional Domain APIs:
- /orchestration/* - Orchestration layer
- /collective/* - Collective intelligence
- /reasoning/* - Reasoning engines
- /memory/* - Memory systems
- /cognition/* - Cognitive capabilities
- /perception/* - Perception systems
- /learning/* - Learning systems
- /resources/* - Resource management
- /knowledge/* - Knowledge systems
- /tools/* - Tool ecosystem
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("BAEL.SingularityAPI")

router = APIRouter(prefix="/singularity", tags=["singularity"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SingularityModeEnum(str, Enum):
    dormant = "dormant"
    awakened = "awakened"
    empowered = "empowered"
    transcendent = "transcendent"
    autonomous = "autonomous"
    godmode = "godmode"


class AwakenRequest(BaseModel):
    mode: SingularityModeEnum = SingularityModeEnum.transcendent
    enable_all: bool = True
    enable_autonomous: bool = False


class ThinkRequest(BaseModel):
    query: str = Field(..., description="The query or task to think about")
    depth: str = Field(default="deep", description="Thinking depth: shallow, medium, deep")
    context: Optional[Dict[str, Any]] = None


class CollectiveRequest(BaseModel):
    problem: str = Field(..., description="The problem to solve collectively")
    strategy: str = Field(default="hybrid", description="Strategy: swarm, council, evolution, hybrid")
    agents: int = Field(default=10, ge=1, le=100, description="Number of agents to use")


class ReasonRequest(BaseModel):
    query: str = Field(..., description="The query to reason about")
    engines: Optional[List[str]] = Field(default=None, description="Specific reasoning engines to use")


class CreateRequest(BaseModel):
    request: str = Field(..., description="What to create")
    mode: str = Field(default="creative", description="Creation mode: creative, innovative, blend")


class LearnRequest(BaseModel):
    experience: Dict[str, Any] = Field(..., description="The experience to learn from")
    learning_type: str = Field(default="feedback", description="Type: feedback, reinforcement, meta, continual")


class ComputerRequest(BaseModel):
    task: str = Field(..., description="The computer task to perform")
    context: Optional[Dict[str, Any]] = None


class ToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MaximumRequest(BaseModel):
    goal: str = Field(..., description="The goal to achieve at maximum potential")
    context: Optional[Dict[str, Any]] = None


class InvokeRequest(BaseModel):
    capability: str = Field(..., description="Name of the capability to invoke")
    method: str = Field(default="process", description="Method to call")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class DecideRequest(BaseModel):
    query: str = Field(..., description="The decision query")
    context: Optional[Dict[str, Any]] = None
    fast_mode: bool = Field(default=False, description="Use fast mode (skip non-essential stages)")


class IntegrateRequest(BaseModel):
    integration_name: str = Field(..., description="Name of the integration to execute")
    input_data: Any = Field(..., description="Input data to process")
    context: Optional[Dict[str, Any]] = None


class SingularityResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    mode: Optional[str] = None


# Global singularity reference
_singularity = None


async def get_singularity():
    """Get or create the singularity instance."""
    global _singularity

    if _singularity is None:
        try:
            from core.singularity import SingularityMode, awaken
            _singularity = await awaken(SingularityMode.TRANSCENDENT)
        except Exception as e:
            logger.error(f"Failed to awaken singularity: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return _singularity


# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@router.post("/awaken", response_model=SingularityResponse)
async def awaken_singularity(request: AwakenRequest):
    """
    Awaken the BAEL Singularity.

    This initializes all capabilities and prepares the system
    for maximum operation.
    """
    try:
        from core.singularity import SingularityMode, awaken

        mode = SingularityMode(request.mode.value)

        global _singularity
        _singularity = await awaken(mode)

        return SingularityResponse(
            success=True,
            data=_singularity.get_status(),
            mode=request.mode.value
        )
    except Exception as e:
        logger.error(f"Awaken failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/think", response_model=SingularityResponse)
async def think(request: ThinkRequest):
    """
    Primary thinking interface.

    Uses the brain with extended thinking for complex queries.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.think(
            query=request.query,
            depth=request.depth,
            context=request.context
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Think failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/collective", response_model=SingularityResponse)
async def collective_solve(request: CollectiveRequest):
    """
    Solve problems using collective intelligence.

    Strategies:
    - swarm: Particle swarm optimization
    - council: Multi-council deliberation
    - evolution: Evolutionary algorithms
    - hybrid: Combine all methods
    """
    try:
        singularity = await get_singularity()
        result = await singularity.collective_solve(
            problem=request.problem,
            strategy=request.strategy,
            agents=request.agents
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Collective solve failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/reason", response_model=SingularityResponse)
async def reason(request: ReasonRequest):
    """
    Apply reasoning engines to a query.

    Available engines:
    - causal_reasoning, counterfactual, temporal_reasoning
    - deductive, inductive, abductive, analogical
    - probabilistic, fuzzy_logic, modal_logic
    - epistemic, deontic, defeasible
    - game_theory, negotiation
    """
    try:
        singularity = await get_singularity()
        result = await singularity.reason(
            query=request.query,
            engines=request.engines
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Reason failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/create", response_model=SingularityResponse)
async def create(request: CreateRequest):
    """
    Creative generation using creativity engine.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.create(
            request=request.request,
            mode=request.mode
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Create failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/learn", response_model=SingularityResponse)
async def learn(request: LearnRequest):
    """
    Learn from an experience.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.learn(
            experience=request.experience,
            learning_type=request.learning_type
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Learn failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/decide", response_model=SingularityResponse)
async def decide(request: DecideRequest):
    """
    🧠 Make a decision using the full 10-stage decision pipeline.

    Stages:
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
    """
    try:
        singularity = await get_singularity()
        result = await singularity.decide(
            query=request.query,
            context=request.context,
            fast_mode=request.fast_mode
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Decide failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/integrate", response_model=SingularityResponse)
async def integrate(request: IntegrateRequest):
    """
    🔗 Execute a capability integration workflow.

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
    """
    try:
        singularity = await get_singularity()
        result = await singularity.integrate(
            integration_name=request.integration_name,
            input_data=request.input_data,
            context=request.context
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Integrate failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.get("/integrations", response_model=SingularityResponse)
async def list_integrations():
    """
    List all available integration workflows.
    """
    try:
        from core.singularity.integration_engine import (
            IntegrationConfig, SingularityIntegrations)

        integrations = {}
        for attr_name in dir(SingularityIntegrations):
            if not attr_name.startswith('_'):
                config = getattr(SingularityIntegrations, attr_name)
                if isinstance(config, IntegrationConfig):
                    integrations[config.name] = {
                        "pattern": config.pattern.value,
                        "capabilities": config.capabilities,
                        "weights": config.weights
                    }

        return SingularityResponse(success=True, data={"integrations": integrations})
    except Exception as e:
        logger.error(f"List integrations failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/evolve", response_model=SingularityResponse)
async def evolve():
    """
    Trigger self-evolution.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.evolve()
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Evolve failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/computer", response_model=SingularityResponse)
async def use_computer(request: ComputerRequest):
    """
    Use computer (desktop automation).
    """
    try:
        singularity = await get_singularity()
        result = await singularity.use_computer(
            task=request.task,
            context=request.context
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Computer use failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/tool", response_model=SingularityResponse)
async def execute_tool(request: ToolRequest):
    """
    Execute any MCP tool.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.execute_tool(
            tool_name=request.tool_name,
            **request.arguments
        )
        return SingularityResponse(success=True, data={"result": result})
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/maximum", response_model=SingularityResponse)
async def maximum_potential(request: MaximumRequest):
    """
    🔥 MAXIMUM POTENTIAL MODE 🔥

    Engage ALL capabilities to achieve the goal.
    This is the ultimate invocation.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.maximum_potential(
            goal=request.goal,
            context=request.context
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Maximum potential failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/invoke", response_model=SingularityResponse)
async def invoke_capability(request: InvokeRequest):
    """
    Invoke any capability directly.

    This provides raw access to any loaded capability.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            capability=request.capability,
            method=request.method,
            **request.arguments
        )
        return SingularityResponse(success=True, data={"result": result})
    except Exception as e:
        logger.error(f"Invoke failed: {e}")
        return SingularityResponse(success=False, error=str(e))


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/status", response_model=SingularityResponse)
async def get_status():
    """
    Get comprehensive Singularity status.
    """
    try:
        singularity = await get_singularity()
        return SingularityResponse(
            success=True,
            data=singularity.get_status(),
            mode=singularity.state.mode.value
        )
    except Exception as e:
        logger.error(f"Status failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.get("/capabilities", response_model=SingularityResponse)
async def list_capabilities():
    """
    List all available capabilities by domain.
    """
    try:
        singularity = await get_singularity()
        return SingularityResponse(
            success=True,
            data=singularity.list_capabilities()
        )
    except Exception as e:
        logger.error(f"List capabilities failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.get("/introspect", response_model=SingularityResponse)
async def introspect():
    """
    Deep introspection of the Singularity.
    """
    try:
        singularity = await get_singularity()
        result = await singularity.introspect()
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Introspect failed: {e}")
        return SingularityResponse(success=False, error=str(e))


@router.post("/mode", response_model=SingularityResponse)
async def set_mode(mode: SingularityModeEnum):
    """
    Change operating mode.
    """
    try:
        from core.singularity import SingularityMode

        singularity = await get_singularity()
        await singularity.set_mode(SingularityMode(mode.value))

        return SingularityResponse(
            success=True,
            data=singularity.get_status(),
            mode=mode.value
        )
    except Exception as e:
        logger.error(f"Set mode failed: {e}")
        return SingularityResponse(success=False, error=str(e))


# =============================================================================
# DOMAIN-SPECIFIC ENDPOINTS
# =============================================================================

# Orchestration
@router.post("/orchestration/process")
async def orchestration_process(task: str, context: Optional[Dict] = None):
    """Process task through orchestration layer."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke("brain", "process_task", task=task, context=context)
        return SingularityResponse(success=True, data={"result": result})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Swarm Operations
@router.post("/collective/swarm/optimize")
async def swarm_optimize(objective: str, agent_count: int = 50, iterations: int = 100):
    """Run swarm optimization."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "swarm_intelligence",
            "optimize",
            objective=objective,
            agent_count=agent_count,
            iterations=iterations
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/collective/swarm/solve")
async def swarm_solve(problem: str, algorithm: str = "pso"):
    """Solve problem using swarm algorithms."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "swarm_intelligence",
            "collective_solve",
            problem=problem,
            algorithm=algorithm
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Council Operations
@router.post("/collective/council/convene")
async def council_convene(topic: str, council_type: str = "grand"):
    """Convene a council for deliberation."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "grand_council",
            "convene",
            topic=topic,
            council_type=council_type
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Evolution Operations
@router.post("/learning/evolution/evolve")
async def evolution_evolve(population_size: int = 50, generations: int = 100):
    """Run evolutionary optimization."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "evolution",
            "evolve",
            population_size=population_size,
            generations=generations
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Cognition Operations
@router.post("/cognition/extended-thinking")
async def extended_thinking(query: str, max_steps: int = 10):
    """Use extended thinking for complex reasoning."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "extended_thinking",
            "think",
            query=query,
            max_steps=max_steps
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/cognition/metacognition")
async def metacognition_analyze(query: str):
    """Perform metacognitive analysis."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "metacognition",
            "analyze",
            query=query
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/cognition/creativity")
async def creativity_generate(prompt: str, mode: str = "divergent"):
    """Generate creative content."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "creativity",
            "generate",
            prompt=prompt,
            mode=mode
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/cognition/curiosity")
async def curiosity_explore(topic: str):
    """Explore a topic driven by curiosity."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "curiosity",
            "explore",
            topic=topic
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Memory Operations
@router.post("/memory/store")
async def memory_store(key: str, value: Any, memory_type: str = "semantic"):
    """Store in memory."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "memory_manager",
            "store",
            key=key,
            value=value,
            memory_type=memory_type
        )
        return SingularityResponse(success=True, data={"stored": True})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.get("/memory/retrieve/{key}")
async def memory_retrieve(key: str):
    """Retrieve from memory."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "memory_manager",
            "retrieve",
            key=key
        )
        return SingularityResponse(success=True, data={"value": result})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/memory/search")
async def memory_search(query: str, limit: int = 10):
    """Search memory."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "memory_manager",
            "search",
            query=query,
            limit=limit
        )
        return SingularityResponse(success=True, data={"results": result})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Reasoning Engines
@router.post("/reasoning/causal")
async def causal_reasoning(query: str):
    """Apply causal reasoning."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke("causal_reasoning", "reason", query=query)
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/reasoning/game-theory")
async def game_theory_analyze(scenario: str, players: int = 2):
    """Analyze using game theory."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "game_theory",
            "analyze",
            scenario=scenario,
            players=players
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/reasoning/negotiation")
async def negotiation_strategize(context: str, parties: List[str] = None):
    """Plan negotiation strategy."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "negotiation",
            "strategize",
            context=context,
            parties=parties or ["party_a", "party_b"]
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Perception
@router.post("/perception/vision/analyze")
async def vision_analyze(image_path: str):
    """Analyze an image."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "vision",
            "analyze",
            image_path=image_path
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/perception/voice/speak")
async def voice_speak(text: str):
    """Convert text to speech."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "voice",
            "speak",
            text=text
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Learning
@router.post("/learning/reinforcement/train")
async def rl_train(environment: str, episodes: int = 1000):
    """Train reinforcement learning agent."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "reinforcement",
            "train",
            environment=environment,
            episodes=episodes
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/learning/nas/search")
async def nas_search(task: str, search_space: str = "standard"):
    """Search for optimal neural architecture."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "nas",
            "search",
            task=task,
            search_space=search_space
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Knowledge
@router.post("/knowledge/rag/query")
async def rag_query(query: str, top_k: int = 5):
    """Query knowledge using RAG."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "rag",
            "query",
            query=query,
            top_k=top_k
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/knowledge/graph/query")
async def graph_query(query: str):
    """Query knowledge graph."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "knowledge_graph",
            "query",
            query=query
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Resources
@router.post("/resources/exploit")
async def exploit_resources(resource_type: str = "api"):
    """Exploit free resources."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "exploitation",
            "exploit",
            resource_type=resource_type
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.get("/resources/status")
async def resource_status():
    """Get resource usage status."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "exploitation",
            "get_status"
        )
        return SingularityResponse(success=True, data=result)
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


# Tools
@router.get("/tools/list")
async def list_tools():
    """List all available MCP tools."""
    try:
        singularity = await get_singularity()
        result = await singularity.invoke(
            "tool_loader",
            "list_tools"
        )
        return SingularityResponse(success=True, data={"tools": result})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))


@router.post("/tools/execute")
async def execute_tool_direct(name: str, args: Dict[str, Any] = None):
    """Execute a specific tool."""
    try:
        singularity = await get_singularity()
        result = await singularity.execute_tool(name, **(args or {}))
        return SingularityResponse(success=True, data={"result": result})
    except Exception as e:
        return SingularityResponse(success=False, error=str(e))
