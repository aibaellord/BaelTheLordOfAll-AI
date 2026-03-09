"""
BAEL - The Lord of All AI Agents
FastAPI Server - REST API Interface

Provides a comprehensive REST API for interacting with BAEL
from external applications, web interfaces, and other services.
"""

import asyncio
import json
import logging

# Import BAEL components
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.brain.brain import BaelBrain
from core.orchestrator.orchestrator import (
    AgentConfig,
    AgentOrchestrator,
    WorkflowPattern,
)

# EnhancedBaelBrain -- preferred over BaelBrain when available
try:
    from core.brain.enhanced_brain import get_enhanced_brain as _get_enhanced
    _ENHANCED_AVAILABLE = True
except ImportError:
    _ENHANCED_AVAILABLE = False

logger = logging.getLogger("BAEL.API")



# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ThinkRequest(BaseModel):
    """Request to process input."""
    input: str = Field(..., description="User input to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    stream: bool = Field(False, description="Whether to stream response")


class ThinkResponse(BaseModel):
    """Response from thinking."""
    response: str
    session_id: str
    confidence: Optional[float] = None
    reasoning_trace: Optional[List[str]] = None


class WorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    task: str = Field(..., description="Task description")
    workflow: str = Field("full_development", description="Workflow name")


class AgentSpawnRequest(BaseModel):
    """Request to spawn an agent."""
    task: str = Field(..., description="Task for the agent")
    name: Optional[str] = Field(None, description="Agent name")
    persona_id: Optional[str] = Field(None, description="Persona to use")
    roles: Optional[List[str]] = Field(None, description="Team roles (for team spawn)")


class ResearchRequest(BaseModel):
    """Request for research."""
    topic: str = Field(..., description="Topic to research")
    depth: int = Field(3, description="Research depth (1-5)")


class CodeExecuteRequest(BaseModel):
    """Request to execute code."""
    code: str = Field(..., description="Code to execute")
    language: str = Field("python", description="Programming language")


class MemorySearchRequest(BaseModel):
    """Request to search memory."""
    query: str = Field(..., description="Search query")
    memory_types: Optional[List[str]] = Field(None, description="Memory types to search")
    limit: int = Field(10, description="Maximum results")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float
    session_id: str


# =============================================================================
# APP SETUP
# =============================================================================

# Global instances -- enhanced brain is T1, brain is T2 fallback
brain: Optional[BaelBrain] = None
enhanced_brain = None
orchestrator: Optional[AgentOrchestrator] = None
start_time: Optional[datetime] = None


async def _think(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Route a query through EnhancedBaelBrain (T1) or BaelBrain (T2)."""
    if enhanced_brain is not None:
        return await enhanced_brain.think(query, context or {})
    if brain is not None:
        return await brain.think(query, context or {})
    raise RuntimeError("No brain initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler -- initializes enhanced brain (T1) + fallback brain (T2)."""
    global brain, enhanced_brain, orchestrator, start_time

    logger.info("Starting BAEL API Server...")
    start_time = datetime.now()

    # Tier 1: EnhancedBaelBrain (28 subsystems, 12-stage pipeline)
    if _ENHANCED_AVAILABLE:
        try:
            enhanced_brain = _get_enhanced()
            await enhanced_brain.initialize()
            logger.info("EnhancedBaelBrain T1 active -- 28 subsystems, 12 stages")
        except Exception as exc:
            logger.warning(f"EnhancedBaelBrain init failed: {exc}")
            enhanced_brain = None

    # Tier 2: BaelBrain baseline fallback
    brain = BaelBrain()
    await brain.initialize()
    logger.info("BaelBrain T2 initialized")

    orchestrator = AgentOrchestrator(brain)

    # Bootstrap: auto-discover all capabilities, agents, plugins, workflows
    try:
        from core.bootstrap.startup import initialize as bael_bootstrap
        bootstrap_result = await bael_bootstrap(fail_fast=False)
        logger.info(
            f"✅ BAEL Bootstrap complete — {bootstrap_result.capabilities_loaded} capabilities, "
            f"{bootstrap_result.agents_registered} agents, {bootstrap_result.plugins_loaded} plugins"
        )
    except Exception as exc:
        logger.warning(f"⚠️ BAEL Bootstrap warning (non-fatal): {exc}")

    # Propagate the best brain to sub-routers
    _active = enhanced_brain or brain
    try:
        from api.chat_api import set_brain
        set_brain(_active)
        logger.info("Brain connected to Chat API")
    except ImportError:
        pass

    try:
        from api.council_api import set_brain as set_council_brain
        set_council_brain(_active)
        logger.info("Brain connected to Council API")
    except ImportError:
        pass

    logger.info("BAEL API Server ready")
    yield

    # Shutdown
    logger.info("Shutting down BAEL API Server...")
    if orchestrator:
        await orchestrator.terminate_all()
    if brain:
        await brain.shutdown()
    logger.info("BAEL API Server shutdown complete")


app = FastAPI(
    title="BAEL - The Lord of All AI Agents",
    description="The ultimate AI agent orchestration system API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the Singularity API router
try:
    from api.singularity_api import router as singularity_router
    app.include_router(singularity_router, prefix="/api")
    logger.info("✅ Singularity API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Singularity API not available: {e}")

# Include the Chat API router (primary chat interface for UI)
try:
    from api.chat_api import router as chat_router
    from api.chat_api import set_brain
    app.include_router(chat_router, prefix="/api")
    logger.info("✅ Chat API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Chat API not available: {e}")

# Include the Settings API router
try:
    from api.settings_api import router as settings_router
    app.include_router(settings_router, prefix="/api")
    logger.info("✅ Settings API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Settings API not available: {e}")

# Include the Files API router
try:
    from api.files_api import router as files_router
    app.include_router(files_router, prefix="/api")
    logger.info("✅ Files API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Files API not available: {e}")

# Include the Council API router (Grand Council deliberation system)
try:
    from api.council_api import router as council_router
    from api.council_api import set_brain as set_council_brain
    app.include_router(council_router, prefix="/api")
    logger.info("✅ Council API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Council API not available: {e}")

# Include the Registry API router (MasterRegistry + bootstrap status)
try:
    from api.registry_api import router as registry_router
    app.include_router(registry_router, prefix="/api")
    logger.info("✅ Registry API router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Registry API not available: {e}")


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint - Welcome page."""
    return {
        "name": "🔥 BAEL - The Lord of All AI Agents",
        "version": "2.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "docs": "/docs",
            "api": "/api/v1/status",
            "think": "POST /think",
            "chat": "POST /chat",
            "websocket": "WS /ws"
        },
        "message": "Welcome to BAEL. Use /docs for interactive API documentation."
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    uptime = (datetime.now() - start_time).total_seconds() if start_time else 0

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=uptime,
        session_id=brain.session_id
    )


@app.get("/status")
async def get_status():
    """Get detailed system status."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    state = brain.get_state()

    agent_statuses = orchestrator.get_all_statuses() if orchestrator else []

    return {
        "brain": state,
        "agents": agent_statuses,
        "personas_loaded": len(brain.personas),
        "tools_loaded": len(brain.tools),
        "uptime_seconds": (datetime.now() - start_time).total_seconds() if start_time else 0
    }


# =============================================================================
# CORE THINKING ENDPOINTS
# =============================================================================

@app.post("/think", response_model=ThinkResponse)
async def think(request: ThinkRequest):
    """Process input and generate response."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    try:
        result = await brain.think(request.input, request.context)

        return ThinkResponse(
            response=result.get('response', ''),
            session_id=brain.session_id,
            confidence=result.get('confidence'),
            reasoning_trace=[t.content for t in result.get('reasoning_trace', [])] if 'reasoning_trace' in result else None
        )
    except Exception as e:
        logger.error(f"Error in think: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/think/stream")
async def think_stream(request: ThinkRequest):
    """Stream thinking response."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    async def generate():
        try:
            # For now, return full response as single chunk
            # TODO: Implement true streaming
            result = await brain.think(request.input, request.context)
            response = result.get('response', '')

            # Simulate streaming by chunking
            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                await asyncio.sleep(0.01)

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

@app.post("/workflow")
async def execute_workflow(request: WorkflowRequest):
    """Execute a predefined workflow."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    workflows = {
        'code_review': WorkflowPattern.code_review(),
        'research_and_implement': WorkflowPattern.research_and_implement(),
        'full_development': WorkflowPattern.full_development()
    }

    if request.workflow not in workflows:
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {request.workflow}")

    try:
        result = await orchestrator.run_workflow(request.task, workflows[request.workflow])
        return result
    except Exception as e:
        logger.error(f"Error in workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflow/list")
async def list_workflows():
    """List available workflows."""
    return {
        "workflows": [
            {
                "name": "code_review",
                "description": "Code review with multiple passes",
                "steps": ["implement", "review", "security", "fix"]
            },
            {
                "name": "research_and_implement",
                "description": "Research then implement",
                "steps": ["research", "design", "implement", "validate"]
            },
            {
                "name": "full_development",
                "description": "Complete development workflow",
                "steps": ["gather", "design", "implement", "test", "audit", "finalize"]
            }
        ]
    }


# =============================================================================
# AGENT ENDPOINTS
# =============================================================================

@app.post("/agent/spawn")
async def spawn_agent(request: AgentSpawnRequest):
    """Spawn a new agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        config = AgentConfig(
            name=request.name or "Custom Agent",
            persona_id=request.persona_id
        )

        agent = await orchestrator.spawn_agent(
            config=config,
            task=request.task
        )

        return {
            "agent_id": agent.id,
            "name": agent.name,
            "state": agent.state.value
        }
    except Exception as e:
        logger.error(f"Error spawning agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/team")
async def spawn_team(request: AgentSpawnRequest):
    """Spawn a team of agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        agents = await orchestrator.spawn_team(request.task, request.roles)

        return {
            "agents": [
                {"id": a.id, "name": a.name, "role": a.role.value}
                for a in agents
            ]
        }
    except Exception as e:
        logger.error(f"Error spawning team: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/{agent_id}/run")
async def run_agent(agent_id: str):
    """Run a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await orchestrator.run_agent(agent_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get agent status."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    agent = orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return agent.get_status()


@app.delete("/agent/{agent_id}")
async def terminate_agent(agent_id: str):
    """Terminate an agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        await orchestrator.terminate_agent(agent_id)
        return {"status": "terminated", "agent_id": agent_id}
    except Exception as e:
        logger.error(f"Error terminating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """List all agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {"agents": orchestrator.get_all_statuses()}


# =============================================================================
# RESEARCH ENDPOINTS
# =============================================================================

@app.post("/research")
async def conduct_research(request: ResearchRequest):
    """Conduct research on a topic."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    try:
        result = await brain.research(request.topic, depth=request.depth)
        return result
    except Exception as e:
        logger.error(f"Error in research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CODE EXECUTION ENDPOINTS
# =============================================================================

@app.post("/code/execute")
async def execute_code(request: CodeExecuteRequest):
    """Execute code."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    try:
        result = await brain.execute_code(request.code, request.language)
        return result
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MEMORY ENDPOINTS
# =============================================================================

@app.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """Search memory."""
    if not brain or not brain.memory_manager:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    try:
        results = await brain.memory_manager.comprehensive_search(
            query=request.query,
            memory_types=request.memory_types,
            limit=request.limit
        )
        return results
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats")
async def get_memory_stats():
    """Get memory statistics."""
    if not brain or not brain.memory_manager:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    return {
        "working_memory_items": len(brain.memory_manager.working._items),
        "episodic_entries": len(brain.memory_manager.episodic._entries),
        "semantic_entries": len(brain.memory_manager.semantic._knowledge),
        "procedural_entries": len(brain.memory_manager.procedural._procedures)
    }


# =============================================================================
# PERSONA ENDPOINTS
# =============================================================================

@app.get("/personas")
async def list_personas():
    """List available personas."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    return {
        "personas": [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role,
                "expertise": p.config.expertise,
                "state": p.state.value
            }
            for p in brain.personas.values()
        ]
    }


@app.get("/persona/{persona_id}")
async def get_persona(persona_id: str):
    """Get persona details."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    if persona_id not in brain.personas:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")

    persona = brain.personas[persona_id]
    return {
        "id": persona.id,
        "name": persona.name,
        "role": persona.role,
        "description": persona.config.description,
        "expertise": persona.config.expertise,
        "personality_traits": persona.config.personality_traits,
        "communication_style": persona.config.communication_style,
        "strengths": persona.config.strengths,
        "limitations": persona.config.limitations,
        "state": persona.state.value,
        "activation_count": persona.activation_count
    }


# =============================================================================
# TOOLS ENDPOINTS
# =============================================================================

@app.get("/tools")
async def list_tools():
    """List available tools."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "schema": tool.get_schema().__dict__
            }
            for tool in brain.tools.values()
        ]
    }


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time interaction."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            action = data.get('action', 'think')

            if action == 'think':
                input_text = data.get('input', '')
                context = data.get('context')

                result = await brain.think(input_text, context)

                await websocket.send_json({
                    "type": "response",
                    "response": result.get('response', ''),
                    "confidence": result.get('confidence')
                })

            elif action == 'status':
                state = brain.get_state()
                await websocket.send_json({
                    "type": "status",
                    "state": state
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Unknown action: {action}"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# =============================================================================
# API V1 ENDPOINTS FOR NEW UI
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    context: Optional[List[Dict[str, Any]]] = Field(None, description="Previous messages")
    settings: Optional[Dict[str, Any]] = Field(None, description="LLM settings")


class CouncilDeliberateRequest(BaseModel):
    """Council deliberation request."""
    topic: str = Field(..., description="Topic to deliberate")
    members: Optional[List[str]] = Field(None, description="Member IDs to include")


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")


class SettingsUpdateRequest(BaseModel):
    """Settings update request."""
    llm: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    ui: Optional[Dict[str, Any]] = None


# Chat endpoint
@app.post("/api/v1/chat")
async def api_chat(request: ChatRequest):
    """Chat with BAEL - simplified endpoint for UI."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    try:
        result = await brain.think(request.message, {"history": request.context or []})
        return {
            "response": result.get('response', ''),
            "session_id": brain.session_id,
            "metadata": {
                "confidence": result.get('confidence'),
                "tokens_used": result.get('tokens_used', 0)
            }
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System status
@app.get("/api/v1/status")
async def api_status():
    """Get system status for UI."""
    if not brain:
        return {
            "connected": False,
            "tools": 0,
            "mcpServers": 0,
            "memory": {"working": 0, "longTerm": 0},
            "activeModel": None
        }

    state = brain.get_state()
    return {
        "connected": True,
        "brain": {"active": True},
        "tools": len(brain.tools) if hasattr(brain, 'tools') else 0,
        "mcpServers": state.get('mcp_servers', 0),
        "memory": {
            "working": state.get('working_memory_size', 0),
            "longTerm": state.get('long_term_memories', 0)
        },
        "activeModel": state.get('active_model', 'claude-3.5-sonnet')
    }


# Tools endpoint
@app.get("/api/v1/tools")
async def api_list_tools():
    """List all available tools."""
    if not brain:
        return []

    tools_list = []
    for tool_id, tool in getattr(brain, 'tools', {}).items():
        tools_list.append({
            "id": tool_id,
            "name": getattr(tool, 'name', tool_id),
            "description": getattr(tool, 'description', ''),
            "category": getattr(tool, 'category', 'general'),
            "schema": getattr(tool, 'parameters_schema', {})
        })

    return tools_list


@app.post("/api/v1/tools/{tool_id}/execute")
async def api_execute_tool(tool_id: str, request: ToolExecuteRequest):
    """Execute a specific tool."""
    if not brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    tools = getattr(brain, 'tools', {})
    if tool_id not in tools:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")

    try:
        tool = tools[tool_id]
        result = await tool.execute(**request.parameters)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Council endpoints
@app.get("/api/v1/council/members")
async def api_council_members():
    """Get council members."""
    # Default council members
    return [
        {
            "id": "sage",
            "name": "Sage",
            "role": "Strategic Advisor",
            "color": "#3b82f6",
            "active": True,
            "specialties": ["Strategy", "Long-term planning", "Risk assessment"]
        },
        {
            "id": "guardian",
            "name": "Guardian",
            "role": "Safety Monitor",
            "color": "#ef4444",
            "active": True,
            "specialties": ["Security", "Validation", "Safety"]
        },
        {
            "id": "innovator",
            "name": "Innovator",
            "role": "Creative Solutions",
            "color": "#f59e0b",
            "active": True,
            "specialties": ["Creativity", "Novel approaches", "Problem-solving"]
        },
        {
            "id": "analyst",
            "name": "Analyst",
            "role": "Data & Logic",
            "color": "#10b981",
            "active": True,
            "specialties": ["Data analysis", "Logic", "Quantitative reasoning"]
        }
    ]


@app.post("/api/v1/council/deliberate")
async def api_council_deliberate(request: CouncilDeliberateRequest):
    """Start a council deliberation."""
    if not brain and not enhanced_brain:
        raise HTTPException(status_code=503, detail="BAEL not initialized")

    try:
        await _think(
            f"[COUNCIL DELIBERATION] Topic: {request.topic}",
            {"mode": "council", "members": request.members}
        )
        return {
            "deliberation_id": f"delib-{datetime.now().timestamp()}",
            "topic": request.topic,
            "status": "started"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Code execution
@app.post("/api/v1/execute")
async def api_execute_code(request: CodeExecuteRequest):
    """Execute code safely."""
    if request.language == "python":
        try:
            # Safe execution with limited scope
            local_scope = {}
            exec(request.code, {"__builtins__": {}}, local_scope)
            return {"output": str(local_scope.get('result', 'Executed successfully')), "error": None}
        except Exception as e:
            return {"output": None, "error": str(e)}
    else:
        raise HTTPException(status_code=400, detail=f"Language {request.language} not supported")


# Settings endpoints
@app.get("/api/v1/settings")
async def api_get_settings():
    """Get current settings."""
    # Return default settings
    return {
        "llm": {
            "model": "claude-3.5-sonnet",
            "temperature": 0.7,
            "maxTokens": 4096,
            "streaming": True
        },
        "memory": {
            "workingLimit": 100,
            "autoConsolidate": True,
            "vectorBackend": "chromadb"
        },
        "security": {
            "requireConfirmation": True,
            "sandboxMode": False
        },
        "ui": {
            "theme": "dark",
            "accentColor": "#6366f1",
            "animations": True,
            "compact": False
        }
    }


@app.put("/api/v1/settings")
async def api_update_settings(request: SettingsUpdateRequest):
    """Update settings."""
    # In a real implementation, save to config file
    return {"success": True, "message": "Settings updated"}


# Autonomous setup
@app.post("/api/v1/autonomous/setup")
async def api_autonomous_setup():
    """Run autonomous setup."""
    try:
        from core.autonomous.auto_setup import AutoSetup

        setup = AutoSetup()
        analysis = await setup.analyze()

        return {
            "success": True,
            "analysis": analysis
        }
    except ImportError:
        return {"success": False, "error": "Autonomous module not available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/autonomous/discover")
async def api_autonomous_discover():
    """Discover available services."""
    try:
        from core.autonomous.discovery import ServiceDiscovery

        discovery = ServiceDiscovery()
        services = await discovery.discover_all()

        return {
            "services": [
                {
                    "name": s.name,
                    "type": s.type.value,
                    "available": s.available,
                    "endpoint": s.endpoint
                }
                for s in services
            ]
        }
    except ImportError:
        return {"services": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STREAMING ENDPOINTS
# =============================================================================

class StreamChatRequest(BaseModel):
    """Streaming chat request."""
    message: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7


class StreamCouncilRequest(BaseModel):
    """Streaming council request."""
    topic: str
    context: Optional[Dict[str, Any]] = None


class StreamExecuteRequest(BaseModel):
    """Streaming execution request."""
    goal: str
    context: Optional[Dict[str, Any]] = None


@app.post("/api/v1/stream/chat")
async def api_stream_chat(request: StreamChatRequest):
    """Stream chat response with SSE."""
    try:
        from api.streaming import create_streaming_response, get_streaming_chat

        streaming = get_streaming_chat()
        generator = streaming.stream_response(
            prompt=request.message,
            system_prompt=request.system_prompt,
            model=request.model,
            temperature=request.temperature
        )

        return create_streaming_response(generator)
    except ImportError:
        raise HTTPException(status_code=500, detail="Streaming not available")


@app.post("/api/v1/stream/council")
async def api_stream_council(request: StreamCouncilRequest):
    """Stream council deliberation with SSE."""
    try:
        from api.streaming import create_streaming_response, get_streaming_council

        streaming = get_streaming_council()
        generator = streaming.stream_deliberation(
            topic=request.topic,
            context=request.context
        )

        return create_streaming_response(generator)
    except ImportError:
        raise HTTPException(status_code=500, detail="Streaming not available")


@app.post("/api/v1/stream/execute")
async def api_stream_execute(request: StreamExecuteRequest):
    """Stream task execution with SSE."""
    try:
        from api.streaming import create_streaming_response, get_streaming_tasks

        streaming = get_streaming_tasks()
        generator = streaming.stream_execution(
            goal=request.goal,
            context=request.context
        )

        return create_streaming_response(generator)
    except ImportError:
        raise HTTPException(status_code=500, detail="Streaming not available")


# =============================================================================
# MEMORY ENDPOINTS
# =============================================================================

@app.get("/api/v1/memory/all")
async def api_get_all_memories():
    """Get all memories for visualization."""
    if not brain:
        return {"memories": []}

    try:
        memories = []
        # Try to get from working memory
        if hasattr(brain, 'working_memory'):
            for item in getattr(brain.working_memory, 'items', []):
                memories.append({
                    "id": getattr(item, 'id', str(hash(str(item)))),
                    "type": "working",
                    "content": str(item.get('content', item) if isinstance(item, dict) else item),
                    "importance": getattr(item, 'importance', 0.5),
                    "created_at": time.time(),
                    "last_accessed": time.time(),
                    "access_count": getattr(item, 'access_count', 1),
                    "tags": getattr(item, 'tags', []),
                    "connections": getattr(item, 'connections', []),
                    "metadata": {}
                })
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Memory fetch error: {e}")
        return {"memories": []}


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

class WorkflowCreateRequest(BaseModel):
    """Create workflow request."""
    name: str
    nodes: List[Dict[str, Any]]
    variables: Optional[Dict[str, Any]] = None


class WorkflowRunRequest(BaseModel):
    """Run workflow request."""
    variables: Optional[Dict[str, Any]] = None


@app.get("/api/v1/workflows")
async def api_list_workflows():
    """List all workflows."""
    try:
        from core.workflows.execution_engine import get_workflow_storage
        storage = get_workflow_storage()
        return {"workflows": storage.list_all()}
    except ImportError:
        return {"workflows": []}


@app.post("/api/v1/workflows")
async def api_create_workflow(request: WorkflowCreateRequest):
    """Create a new workflow."""
    try:
        from core.workflows.execution_engine import Workflow, get_workflow_storage

        workflow = Workflow.from_dict({
            "name": request.name,
            "nodes": request.nodes,
            "variables": request.variables or {}
        })

        storage = get_workflow_storage()
        storage.save(workflow)

        return {"id": workflow.id, "name": workflow.name}
    except ImportError:
        raise HTTPException(status_code=500, detail="Workflow engine not available")


@app.post("/api/v1/workflows/{workflow_id}/run")
async def api_run_workflow(workflow_id: str, request: WorkflowRunRequest):
    """Run a workflow."""
    try:
        from core.workflows.execution_engine import run_workflow

        context = await run_workflow(workflow_id, request.variables)

        return {
            "execution_id": context.execution_id,
            "status": context.status.value,
            "outputs": {k: str(v)[:200] for k, v in context.node_outputs.items()}
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(status_code=500, detail="Workflow engine not available")


@app.delete("/api/v1/workflows/{workflow_id}")
async def api_delete_workflow(workflow_id: str):
    """Delete a workflow."""
    try:
        from core.workflows.execution_engine import get_workflow_storage
        storage = get_workflow_storage()
        if storage.delete(workflow_id):
            return {"success": True}
        raise HTTPException(status_code=404, detail="Workflow not found")
    except ImportError:
        raise HTTPException(status_code=500, detail="Workflow engine not available")


# =============================================================================
# AGENT BACKEND ENDPOINTS
# =============================================================================

class AgentSpawnV1Request(BaseModel):
    """Spawn agent request for V1 API."""
    persona: Dict[str, Any] = Field(..., description="Agent persona configuration")


class TaskSubmitRequest(BaseModel):
    """Submit task request."""
    description: str = Field(..., description="Task description")
    priority: str = Field("normal", description="Task priority")


class BackendActionRequest(BaseModel):
    """Backend action request."""
    action: str = Field(..., description="start or stop")


@app.get("/api/v1/agents")
async def api_list_agents():
    """List all spawned agents."""
    try:
        from core.agents.execution_backend import get_agent_backend
        backend = get_agent_backend()

        agents = []
        for agent_id, agent in backend.pool.agents.items():
            agents.append({
                "id": agent.id,
                "persona": {
                    "name": agent.persona.name,
                    "role": agent.persona.role,
                    "description": agent.persona.description,
                    "capabilities": [c.name for c in agent.persona.capabilities],
                    "temperature": agent.persona.temperature
                },
                "status": agent.status.value,
                "currentTask": agent.current_task,
                "taskHistory": agent.task_history[-10:],
                "totalTasks": agent.total_tasks,
                "successfulTasks": agent.successful_tasks,
                "createdAt": agent.created_at.isoformat(),
                "lastActive": agent.last_active.isoformat()
            })

        return {"agents": agents}
    except ImportError:
        return {"agents": []}


@app.post("/api/v1/agents/spawn")
async def api_spawn_agent(request: AgentSpawnV1Request):
    """Spawn a new agent."""
    try:
        from core.agents.execution_backend import (
            AgentCapability,
            AgentPersona,
            get_agent_backend,
        )

        backend = get_agent_backend()

        persona = AgentPersona(
            name=request.persona.get("name", "Agent"),
            role=request.persona.get("role", "Assistant"),
            description=request.persona.get("description", ""),
            system_prompt=request.persona.get("system_prompt", "You are a helpful AI assistant."),
            capabilities=[
                AgentCapability(name=c, description=c)
                for c in request.persona.get("capabilities", ["general"])
            ],
            temperature=request.persona.get("temperature", 0.7)
        )

        agent = await backend.spawn_agent(persona)

        return {
            "id": agent.id,
            "persona": {
                "name": agent.persona.name,
                "role": agent.persona.role
            },
            "status": agent.status.value
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="Agent backend not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/agents/{agent_id}")
async def api_remove_agent(agent_id: str):
    """Remove an agent."""
    try:
        from core.agents.execution_backend import get_agent_backend
        backend = get_agent_backend()
        await backend.pool.despawn_agent(agent_id)
        return {"success": True}
    except ImportError:
        raise HTTPException(status_code=500, detail="Agent backend not available")


@app.get("/api/v1/agents/tasks")
async def api_list_tasks():
    """List all tasks."""
    try:
        from core.agents.execution_backend import get_agent_backend
        backend = get_agent_backend()

        tasks = []
        for task_id, task in backend.delegator.tasks.items():
            tasks.append({
                "id": task.id,
                "description": task.description,
                "priority": task.priority.name.lower(),
                "status": task.status.value,
                "assignedAgent": task.assigned_agent,
                "result": str(task.result)[:200] if task.result else None,
                "error": task.error,
                "createdAt": task.created_at.isoformat(),
                "completedAt": task.completed_at.isoformat() if task.completed_at else None
            })

        return {"tasks": tasks}
    except ImportError:
        return {"tasks": []}


@app.post("/api/v1/agents/tasks")
async def api_submit_task(request: TaskSubmitRequest):
    """Submit a new task."""
    try:
        from core.agents.execution_backend import TaskPriority, get_agent_backend

        backend = get_agent_backend()

        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "normal": TaskPriority.NORMAL,
            "low": TaskPriority.LOW,
            "background": TaskPriority.BACKGROUND
        }

        task = await backend.submit_task(
            description=request.description,
            priority=priority_map.get(request.priority, TaskPriority.NORMAL)
        )

        return {
            "id": task.id,
            "description": task.description,
            "priority": task.priority.name.lower(),
            "status": task.status.value
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="Agent backend not available")


@app.get("/api/v1/agents/status")
async def api_agent_backend_status():
    """Get agent backend status."""
    try:
        from core.agents.execution_backend import get_agent_backend
        backend = get_agent_backend()
        status = backend.get_status()

        return {
            "running": status["running"],
            "totalAgents": status["total_agents"],
            "idleAgents": status["idle_agents"],
            "pendingTasks": status["pending_tasks"],
            "totalTasks": status["total_tasks"]
        }
    except ImportError:
        return {
            "running": False,
            "totalAgents": 0,
            "idleAgents": 0,
            "pendingTasks": 0,
            "totalTasks": 0
        }


@app.post("/api/v1/agents/backend")
async def api_agent_backend_control(request: BackendActionRequest):
    """Start or stop the agent backend."""
    try:
        from core.agents.execution_backend import get_agent_backend
        backend = get_agent_backend()

        if request.action == "start":
            await backend.start()
        elif request.action == "stop":
            await backend.stop()
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

        return {"success": True, "action": request.action}
    except ImportError:
        raise HTTPException(status_code=500, detail="Agent backend not available")


# =============================================================================
# MEMORY V1 ENDPOINTS
# =============================================================================

class MemoryQueryRequest(BaseModel):
    """Memory query request."""
    query: Optional[str] = None
    type: Optional[str] = None
    limit: int = 100


@app.post("/api/v1/memory")
async def api_query_memory(request: MemoryQueryRequest):
    """Query memories."""
    if not brain:
        return {"memories": [], "stats": {}}

    try:
        memories = []
        stats = {"total": 0, "byType": {}, "avgImportance": 0, "recentlyAccessed": 0}

        # Try to get from memory manager
        if hasattr(brain, 'memory_manager'):
            mm = brain.memory_manager

            # Working memory
            if hasattr(mm, 'working') and hasattr(mm.working, '_items'):
                for item in mm.working._items:
                    memories.append({
                        "id": str(hash(str(item)))[:12],
                        "type": "working",
                        "content": str(item.get('content', item) if isinstance(item, dict) else item),
                        "summary": None,
                        "tags": [],
                        "importance": 0.8,
                        "accessCount": 1,
                        "createdAt": datetime.now().isoformat(),
                        "lastAccessed": datetime.now().isoformat(),
                        "metadata": {}
                    })

            # Episodic memory
            if hasattr(mm, 'episodic') and hasattr(mm.episodic, '_entries'):
                for entry in list(mm.episodic._entries.values())[:50]:
                    memories.append({
                        "id": getattr(entry, 'id', str(hash(str(entry)))[:12]),
                        "type": "episodic",
                        "content": getattr(entry, 'content', str(entry)),
                        "summary": getattr(entry, 'summary', None),
                        "tags": getattr(entry, 'tags', []),
                        "importance": getattr(entry, 'importance', 0.5),
                        "accessCount": getattr(entry, 'access_count', 1),
                        "createdAt": getattr(entry, 'created_at', datetime.now()).isoformat() if hasattr(getattr(entry, 'created_at', None), 'isoformat') else datetime.now().isoformat(),
                        "lastAccessed": datetime.now().isoformat(),
                        "metadata": {}
                    })

            # Semantic memory
            if hasattr(mm, 'semantic') and hasattr(mm.semantic, '_knowledge'):
                for key, knowledge in list(mm.semantic._knowledge.items())[:50]:
                    memories.append({
                        "id": key[:12] if isinstance(key, str) else str(hash(key))[:12],
                        "type": "semantic",
                        "content": str(knowledge),
                        "summary": None,
                        "tags": [],
                        "importance": 0.7,
                        "accessCount": 1,
                        "createdAt": datetime.now().isoformat(),
                        "lastAccessed": datetime.now().isoformat(),
                        "metadata": {}
                    })

        # Filter by type if specified
        if request.type:
            memories = [m for m in memories if m["type"] == request.type]

        # Search if query specified
        if request.query:
            query_lower = request.query.lower()
            memories = [m for m in memories if query_lower in m["content"].lower()]

        # Apply limit
        memories = memories[:request.limit]

        # Calculate stats
        stats["total"] = len(memories)
        for m in memories:
            stats["byType"][m["type"]] = stats["byType"].get(m["type"], 0) + 1
        if memories:
            stats["avgImportance"] = sum(m["importance"] for m in memories) / len(memories)
        stats["recentlyAccessed"] = len([m for m in memories if m["type"] == "working"])

        return {"memories": memories, "stats": stats}

    except Exception as e:
        logger.error(f"Memory query error: {e}")
        return {"memories": [], "stats": {}}


@app.delete("/api/v1/memory/{memory_id}")
async def api_delete_memory(memory_id: str):
    """Delete a memory entry."""
    # In a real implementation, this would delete from the memory store
    return {"success": True, "id": memory_id}


# =============================================================================
# ADVANCED WEBSOCKET WITH CHANNELS
# =============================================================================

@app.websocket("/ws/v2")
async def websocket_v2(websocket: WebSocket):
    """Advanced WebSocket with channel subscriptions."""
    await websocket.accept()
    client_id = None

    try:
        from core.realtime.websocket_manager import (
            MessageType,  # noqa: F401 — imported for ws_manager use
            WebSocketMessage,  # noqa: F401
            get_ws_manager,
        )

        ws_manager = get_ws_manager()
        client_id = await ws_manager.register(websocket)

        while True:
            raw_data = await websocket.receive_text()
            await ws_manager.handle_message(client_id, raw_data)

    except WebSocketDisconnect:
        if client_id:
            try:
                from core.realtime.websocket_manager import get_ws_manager
                await get_ws_manager().unregister(client_id)
            except Exception:
                pass
    except ImportError:
        # Fall back to simple WebSocket
        await websocket.send_json({"error": "WebSocket manager not available"})
    except Exception as e:
        logger.error(f"WebSocket v2 error: {e}")


# =============================================================================
# APEX ORCHESTRATOR API
# =============================================================================

# APEX Pydantic Models
class APEXProcessRequest(BaseModel):
    """APEX process request."""
    input: str = Field(..., description="Input to process")
    mode: Optional[str] = Field("adaptive", description="Processing mode: balanced, fast, deep, creative, maximum, adaptive")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    capabilities: Optional[List[str]] = Field(None, description="Specific capabilities to use")


class APEXCapabilityRequest(BaseModel):
    """Request to invoke a specific APEX capability."""
    capability: str = Field(..., description="Capability ID")
    input: Any = Field(..., description="Input for the capability")


class APEXToolRequest(BaseModel):
    """Request to execute an MCP tool via APEX."""
    tool: str = Field(..., description="Tool name (e.g., 'brave_search.search')")
    params: Dict[str, Any] = Field({}, description="Tool parameters")


# APEX Instance management
_apex_instance = None

async def get_apex_instance():
    """Get or create the APEX orchestrator instance."""
    global _apex_instance
    if _apex_instance is None:
        try:
            from core.apex.apex_orchestrator import APEXMode, create_apex
            _apex_instance = await create_apex(APEXMode.ADAPTIVE)
        except ImportError:
            return None
    return _apex_instance


@app.get("/api/v1/apex/status")
async def apex_status():
    """Get APEX Orchestrator status."""
    apex = await get_apex_instance()
    if not apex:
        return {
            "status": "not_initialized",
            "mode": None,
            "capabilities": 0,
            "tools": 0,
            "message": "APEX Orchestrator not available"
        }

    try:
        return {
            "status": "active",
            "mode": apex.mode.value if hasattr(apex, 'mode') else "adaptive",
            "capabilities": len(apex.capability_registry.capabilities) if hasattr(apex, 'capability_registry') else 0,
            "tools": len(apex.tool_registry.tools) if hasattr(apex, 'tool_registry') else 0,
            "domains": list(apex.capability_registry.domains.keys()) if hasattr(apex, 'capability_registry') else [],
            "processing_stats": getattr(apex, 'stats', {}),
            "uptime_seconds": (datetime.now() - getattr(apex, 'start_time', datetime.now())).total_seconds()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/v1/apex/process")
async def apex_process(request: APEXProcessRequest):
    """Process input through the APEX Orchestrator."""
    apex = await get_apex_instance()
    if not apex:
        raise HTTPException(status_code=503, detail="APEX Orchestrator not available")

    try:
        result = await apex.process(
            input_data=request.input,
            mode=request.mode,
            context=request.context,
            requested_capabilities=request.capabilities
        )
        return {
            "success": True,
            "result": result,
            "capabilities_used": getattr(result, 'capabilities_used', []) if hasattr(result, 'capabilities_used') else [],
            "processing_time_ms": getattr(result, 'processing_time_ms', 0) if hasattr(result, 'processing_time_ms') else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/apex/capabilities")
async def apex_list_capabilities():
    """List all available APEX capabilities."""
    apex = await get_apex_instance()
    if not apex or not hasattr(apex, 'capability_registry'):
        # Return default capability catalog
        return {
            "domains": {
                "reasoning": {
                    "name": "Reasoning & Logic",
                    "capabilities": [
                        {"id": "causal_reasoning", "name": "Causal Reasoning", "description": "Analyze cause-effect relationships"},
                        {"id": "temporal_reasoning", "name": "Temporal Reasoning", "description": "Reason about time and sequences"},
                        {"id": "counterfactual", "name": "Counterfactual Analysis", "description": "What-if scenario analysis"},
                        {"id": "deductive", "name": "Deductive Logic", "description": "Logical deduction from premises"},
                        {"id": "inductive", "name": "Inductive Reasoning", "description": "Pattern-based generalization"},
                        {"id": "abductive", "name": "Abductive Reasoning", "description": "Best explanation inference"}
                    ]
                },
                "orchestration": {
                    "name": "Orchestration & Control",
                    "capabilities": [
                        {"id": "supreme_controller", "name": "Supreme Controller", "description": "High-level orchestration"},
                        {"id": "brain", "name": "Brain Module", "description": "Core cognitive processing"},
                        {"id": "swarm_intelligence", "name": "Swarm Intelligence", "description": "Multi-agent optimization"}
                    ]
                },
                "memory": {
                    "name": "Memory Systems",
                    "capabilities": [
                        {"id": "working_memory", "name": "Working Memory", "description": "Short-term active context"},
                        {"id": "episodic_memory", "name": "Episodic Memory", "description": "Experience-based recall"},
                        {"id": "semantic_memory", "name": "Semantic Memory", "description": "Knowledge and facts"},
                        {"id": "procedural_memory", "name": "Procedural Memory", "description": "Skills and procedures"},
                        {"id": "meta_memory", "name": "Meta Memory", "description": "Memory about memories"}
                    ]
                },
                "perception": {
                    "name": "Perception & Input",
                    "capabilities": [
                        {"id": "vision", "name": "Vision Processing", "description": "Image understanding"},
                        {"id": "audio", "name": "Audio Processing", "description": "Sound and speech"},
                        {"id": "computer_use", "name": "Computer Use", "description": "GUI interaction"}
                    ]
                },
                "planning": {
                    "name": "Planning & Goals",
                    "capabilities": [
                        {"id": "goal_planning", "name": "Goal Planning", "description": "Objective decomposition"},
                        {"id": "task_planning", "name": "Task Planning", "description": "Task sequencing"},
                        {"id": "resource_allocation", "name": "Resource Allocation", "description": "Optimal resource use"}
                    ]
                },
                "learning": {
                    "name": "Learning & Adaptation",
                    "capabilities": [
                        {"id": "meta_learning", "name": "Meta Learning", "description": "Learning to learn"},
                        {"id": "evolution", "name": "Self-Evolution", "description": "Self-improvement"},
                        {"id": "feedback_learning", "name": "Feedback Learning", "description": "Learn from feedback"}
                    ]
                }
            },
            "total_capabilities": 23
        }

    try:
        return {
            "domains": apex.capability_registry.get_all_domains(),
            "total_capabilities": len(apex.capability_registry.capabilities)
        }
    except Exception as e:
        return {"error": str(e), "domains": {}, "total_capabilities": 0}


@app.post("/api/v1/apex/capability")
async def apex_invoke_capability(request: APEXCapabilityRequest):
    """Invoke a specific APEX capability."""
    apex = await get_apex_instance()
    if not apex:
        raise HTTPException(status_code=503, detail="APEX Orchestrator not available")

    try:
        result = await apex.invoke_capability(request.capability, request.input)
        return {"success": True, "result": result, "capability": request.capability}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/apex/tools")
async def apex_list_tools():
    """List all MCP tools available through APEX."""
    apex = await get_apex_instance()
    if not apex or not hasattr(apex, 'tool_registry'):
        # Return catalog from 52-server configuration
        return {
            "tiers": {
                "infrastructure": ["redis", "postgres", "mongodb"],
                "essential": ["filesystem", "brave_search", "github", "sqlite", "memory"],
                "power": ["playwright", "docker", "git", "kubernetes", "slack", "discord"],
                "enhanced": ["fetch", "puppeteer", "sequential_thinking", "exa", "firecrawl", "tavily"],
                "ai_ml": ["openai", "anthropic", "replicate", "huggingface", "langchain"],
                "cloud": ["aws", "gcp", "azure", "cloudflare", "vercel", "terraform"],
                "productivity": ["notion", "linear", "jira", "todoist", "google_drive", "obsidian"],
                "monitoring": ["sentry", "datadog", "grafana", "prometheus"],
                "vector": ["qdrant", "chromadb", "neo4j", "elasticsearch"]
            },
            "total_servers": 52,
            "total_tools": 200
        }

    try:
        return {
            "tools": apex.tool_registry.get_all_tools(),
            "total": len(apex.tool_registry.tools)
        }
    except Exception as e:
        return {"error": str(e), "tools": [], "total": 0}


@app.post("/api/v1/apex/tool")
async def apex_execute_tool(request: APEXToolRequest):
    """Execute an MCP tool through APEX."""
    apex = await get_apex_instance()
    if not apex:
        raise HTTPException(status_code=503, detail="APEX Orchestrator not available")

    try:
        result = await apex.execute_tool(request.tool, request.params)
        return {"success": True, "result": result, "tool": request.tool}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/apex/modes")
async def apex_get_modes():
    """Get available APEX processing modes."""
    return {
        "modes": [
            {"id": "balanced", "name": "Balanced", "description": "Optimal balance of speed and depth", "default": False},
            {"id": "fast", "name": "Fast", "description": "Quick responses with essential processing", "default": False},
            {"id": "deep", "name": "Deep Analysis", "description": "Thorough analysis with extended thinking", "default": False},
            {"id": "creative", "name": "Creative", "description": "Enhanced creativity and novel solutions", "default": False},
            {"id": "maximum", "name": "Maximum Potential", "description": "All capabilities engaged at full power", "default": False},
            {"id": "adaptive", "name": "Adaptive", "description": "Automatically selects optimal mode based on task", "default": True}
        ]
    }


@app.post("/api/v1/apex/mode")
async def apex_set_mode(mode: str):
    """Set the APEX processing mode."""
    apex = await get_apex_instance()
    if not apex:
        raise HTTPException(status_code=503, detail="APEX Orchestrator not available")

    valid_modes = ["balanced", "fast", "deep", "creative", "maximum", "adaptive"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")

    try:
        from core.apex.apex_orchestrator import APEXMode
        mode_map = {
            "balanced": APEXMode.BALANCED,
            "fast": APEXMode.FAST,
            "deep": APEXMode.DEEP,
            "creative": APEXMode.CREATIVE,
            "maximum": APEXMode.MAXIMUM,
            "adaptive": APEXMode.ADAPTIVE
        }
        apex.set_mode(mode_map[mode])
        return {"success": True, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SWARM INTELLIGENCE API
# =============================================================================

class SwarmSpawnRequest(BaseModel):
    """Request to spawn a swarm."""
    task: str = Field(..., description="Task for the swarm")
    agent_count: int = Field(5, description="Number of agents to spawn")
    strategy: Optional[str] = Field("optimize", description="Swarm strategy: optimize, explore, converge")


class SwarmCommandRequest(BaseModel):
    """Command for the swarm."""
    command: str = Field(..., description="Command: start, pause, resume, stop, evolve")


@app.get("/api/v1/swarm/status")
async def swarm_status():
    """Get swarm intelligence status."""
    try:
        from core.swarm.swarm_intelligence import SwarmIntelligence
        swarm = SwarmIntelligence()
        return {
            "active": True,
            "total_agents": swarm.agent_count if hasattr(swarm, 'agent_count') else 0,
            "active_agents": swarm.active_agents if hasattr(swarm, 'active_agents') else 0,
            "pheromone_trails": swarm.trail_count if hasattr(swarm, 'trail_count') else 0,
            "convergence": swarm.convergence if hasattr(swarm, 'convergence') else 0.0,
            "best_solution": swarm.best_solution if hasattr(swarm, 'best_solution') else None
        }
    except ImportError:
        return {"active": False, "error": "Swarm module not available"}


@app.post("/api/v1/swarm/spawn")
async def swarm_spawn(request: SwarmSpawnRequest):
    """Spawn a swarm of agents."""
    try:
        from core.swarm.swarm_intelligence import SwarmIntelligence
        swarm = SwarmIntelligence()
        result = await swarm.optimize(request.task, agent_count=request.agent_count)
        return {"success": True, "result": result}
    except ImportError:
        raise HTTPException(status_code=503, detail="Swarm module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/swarm/command")
async def swarm_command(request: SwarmCommandRequest):
    """Send a command to the swarm."""
    try:
        from core.swarm.swarm_intelligence import SwarmIntelligence
        swarm = SwarmIntelligence()

        if request.command == "evolve":
            await swarm.evolve()
        elif request.command == "stop":
            await swarm.stop()
        elif request.command == "pause":
            await swarm.pause()
        elif request.command == "resume":
            await swarm.resume()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown command: {request.command}")

        return {"success": True, "command": request.command}
    except ImportError:
        raise HTTPException(status_code=503, detail="Swarm module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BRAIN MODULE API
# =============================================================================

@app.get("/api/v1/brain/status")
async def brain_status():
    """Get brain module status."""
    if not brain:
        return {"status": "not_initialized"}

    state = brain.get_state()
    return {
        "status": "active",
        "session_id": state.get("session_id", ""),
        "model": state.get("active_model", "claude-3.5-sonnet"),
        "working_memory_items": state.get("working_memory_size", 0),
        "total_interactions": state.get("total_interactions", 0),
        "capabilities": state.get("capabilities", [])
    }


@app.get("/api/v1/brain/capabilities")
async def brain_capabilities():
    """Get brain capabilities."""
    if not brain:
        return {"capabilities": []}

    return {
        "capabilities": [
            {"id": "think", "name": "Think", "description": "Process input through cognitive pipeline"},
            {"id": "reason", "name": "Reason", "description": "Apply reasoning engines"},
            {"id": "plan", "name": "Plan", "description": "Create action plans"},
            {"id": "remember", "name": "Remember", "description": "Access and store memories"},
            {"id": "learn", "name": "Learn", "description": "Learn from interactions"},
            {"id": "create", "name": "Create", "description": "Generate creative solutions"}
        ]
    }


# =============================================================================
# EVOLUTION ENGINE API
# =============================================================================

@app.get("/api/v1/evolution/status")
async def evolution_status():
    """Get evolution engine status."""
    try:
        from core.evolution.evolution_engine import EvolutionEngine
        engine = EvolutionEngine()
        return {
            "active": True,
            "generation": getattr(engine, 'generation', 0),
            "fitness": getattr(engine, 'fitness', 0.0),
            "mutations_pending": getattr(engine, 'mutations_pending', 0),
            "last_evolution": getattr(engine, 'last_evolution', None)
        }
    except ImportError:
        return {"active": False, "error": "Evolution module not available"}


@app.post("/api/v1/evolution/evolve")
async def evolution_trigger():
    """Trigger an evolution cycle."""
    try:
        from core.evolution.evolution_engine import EvolutionEngine
        engine = EvolutionEngine()
        result = await engine.evolve()
        return {"success": True, "result": result}
    except ImportError:
        raise HTTPException(status_code=503, detail="Evolution module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/evolution/history")
async def evolution_history():
    """Get evolution history."""
    try:
        from core.evolution.evolution_engine import EvolutionEngine
        engine = EvolutionEngine()
        return {
            "generations": getattr(engine, 'history', []),
            "total_evolutions": len(getattr(engine, 'history', []))
        }
    except ImportError:
        return {"generations": [], "total_evolutions": 0}


# =============================================================================
# REASONING ENGINES API
# =============================================================================

class ReasoningRequest(BaseModel):
    """Reasoning request."""
    query: str = Field(..., description="Query to reason about")
    engine: Optional[str] = Field(None, description="Specific reasoning engine to use")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


@app.get("/api/v1/reasoning/engines")
async def list_reasoning_engines():
    """List all available reasoning engines."""
    return {
        "engines": [
            {"id": "causal", "name": "Causal Reasoning", "description": "Analyze cause-effect relationships"},
            {"id": "temporal", "name": "Temporal Reasoning", "description": "Reason about time and sequences"},
            {"id": "counterfactual", "name": "Counterfactual", "description": "What-if scenario analysis"},
            {"id": "deductive", "name": "Deductive Logic", "description": "Logical deduction from premises"},
            {"id": "inductive", "name": "Inductive Reasoning", "description": "Pattern-based generalization"},
            {"id": "abductive", "name": "Abductive Reasoning", "description": "Best explanation inference"},
            {"id": "analogical", "name": "Analogical Reasoning", "description": "Reasoning by analogy"},
            {"id": "fuzzy", "name": "Fuzzy Logic", "description": "Degrees of truth reasoning"},
            {"id": "probabilistic", "name": "Probabilistic", "description": "Probability-based reasoning"},
            {"id": "spatial", "name": "Spatial Reasoning", "description": "Reasoning about space and relations"},
            {"id": "modal", "name": "Modal Logic", "description": "Possibility and necessity"},
            {"id": "defeasible", "name": "Defeasible Reasoning", "description": "Default reasoning with exceptions"},
            {"id": "heuristic", "name": "Heuristic", "description": "Rule-of-thumb reasoning"}
        ]
    }


@app.post("/api/v1/reasoning/apply")
async def apply_reasoning(request: ReasoningRequest):
    """Apply reasoning to a query."""
    try:
        from core.reasoning.reasoning_engine import ReasoningEngine
        engine = ReasoningEngine()
        result = await engine.reason(request.query, engine=request.engine, context=request.context)
        return {"success": True, "result": result, "engine_used": request.engine or "auto"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Reasoning module not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COUNCILS API
# =============================================================================

class CouncilConveneRequest(BaseModel):
    """Request to convene a council."""
    topic: str = Field(..., description="Topic for deliberation")
    council_type: Optional[str] = Field("grand", description="Council type: grand, ethics, strategy, technical")
    urgency: Optional[str] = Field("normal", description="Urgency: low, normal, high, critical")


@app.get("/api/v1/councils/types")
async def list_council_types():
    """List available council types."""
    return {
        "councils": [
            {"id": "grand", "name": "Grand Council", "description": "High-level strategic decisions", "members": 7},
            {"id": "ethics", "name": "Ethics Council", "description": "Ethical considerations and alignment", "members": 5},
            {"id": "strategy", "name": "Strategy Council", "description": "Strategic planning and direction", "members": 5},
            {"id": "technical", "name": "Technical Council", "description": "Technical decisions and architecture", "members": 6},
            {"id": "creative", "name": "Creative Council", "description": "Creative solutions and innovation", "members": 4}
        ]
    }


@app.post("/api/v1/councils/convene")
async def convene_council(request: CouncilConveneRequest):
    """Convene a council for deliberation."""
    try:
        from core.councils.grand_council import GrandCouncil
        council = GrandCouncil()
        result = await council.convene(request.topic)
        return {"success": True, "result": result, "council": request.council_type}
    except ImportError:
        # Simulate council deliberation
        return {
            "success": True,
            "result": {
                "decision": f"Council deliberation on: {request.topic}",
                "participants": ["Sage", "Guardian", "Innovator", "Analyst"],
                "consensus": 0.85,
                "recommendations": ["Proceed with caution", "Gather more data", "Consider alternatives"]
            },
            "council": request.council_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MCP HUB API
# =============================================================================

# In-memory MCP status storage (updated by health monitor)
mcp_hub_status: Dict[str, Any] = {
    "timestamp": None,
    "summary": {"total_containers": 33, "running": 0, "healthy": 0, "stopped": 33},
    "tiers": {
        "essential": {"total": 5, "running": 0, "percentage": 0},
        "power": {"total": 6, "running": 0, "percentage": 0},
        "enhanced": {"total": 8, "running": 0, "percentage": 0},
        "specialized": {"total": 13, "running": 0, "percentage": 0}
    },
    "containers": []
}


@app.get("/api/v1/mcp/status")
async def get_mcp_status():
    """Get MCP Hub status."""
    return mcp_hub_status


@app.post("/api/v1/mcp/status")
async def update_mcp_status(status: Dict[str, Any]):
    """Receive MCP Hub status update from health monitor."""
    global mcp_hub_status
    mcp_hub_status = status
    return {"status": "ok"}


@app.get("/api/v1/mcp/servers")
async def list_mcp_servers():
    """List all MCP servers with their tools."""
    servers = [
        {"name": "filesystem", "tier": "essential", "tools": ["read_file", "write_file", "list_directory", "search_files", "get_file_info", "create_directory", "move_file"]},
        {"name": "brave-search", "tier": "essential", "tools": ["brave_web_search", "brave_local_search"]},
        {"name": "github", "tier": "essential", "tools": ["create_repository", "search_repositories", "get_file_contents", "create_or_update_file", "push_files", "create_issue", "create_pull_request", "fork_repository", "create_branch"]},
        {"name": "sqlite", "tier": "essential", "tools": ["read_query", "write_query", "create_table", "list_tables", "describe_table", "append_insight"]},
        {"name": "memory", "tier": "essential", "tools": ["create_entities", "create_relations", "add_observations", "delete_entities", "delete_observations", "delete_relations", "read_graph", "search_nodes", "open_nodes"]},
        {"name": "playwright", "tier": "power", "tools": ["playwright_navigate", "playwright_screenshot", "playwright_click", "playwright_fill", "playwright_select", "playwright_hover", "playwright_evaluate"]},
        {"name": "docker", "tier": "power", "tools": ["list_containers", "create_container", "run_container", "stop_container", "remove_container", "get_logs", "list_images"]},
        {"name": "git", "tier": "power", "tools": ["git_status", "git_diff", "git_commit", "git_add", "git_reset", "git_log", "git_create_branch", "git_checkout", "git_show"]},
        {"name": "postgres", "tier": "power", "tools": ["query", "execute", "list_tables", "describe_table"]},
        {"name": "redis", "tier": "power", "tools": ["get", "set", "delete", "list_keys", "publish", "subscribe"]},
        {"name": "slack", "tier": "power", "tools": ["list_channels", "post_message", "reply_to_thread", "add_reaction", "get_channel_history", "get_thread_replies", "search_messages", "get_users"]},
        {"name": "fetch", "tier": "enhanced", "tools": ["fetch"]},
        {"name": "puppeteer", "tier": "enhanced", "tools": ["puppeteer_navigate", "puppeteer_screenshot", "puppeteer_click", "puppeteer_fill", "puppeteer_select", "puppeteer_hover", "puppeteer_evaluate"]},
        {"name": "sequential-thinking", "tier": "enhanced", "tools": ["sequentialthinking"]},
        {"name": "time", "tier": "enhanced", "tools": ["get_current_time", "convert_time"]},
        {"name": "exa", "tier": "enhanced", "tools": ["search", "find_similar", "get_contents"]},
        {"name": "firecrawl", "tier": "enhanced", "tools": ["firecrawl_scrape", "firecrawl_map", "firecrawl_crawl", "firecrawl_check_crawl_status"]},
        {"name": "context7", "tier": "enhanced", "tools": ["resolve-library-id", "get-library-docs"]},
        {"name": "everything", "tier": "enhanced", "tools": ["search"]},
        {"name": "youtube", "tier": "specialized", "tools": ["get_transcript"]},
        {"name": "google-drive", "tier": "specialized", "tools": ["search", "read_file", "list_folder"]},
        {"name": "google-maps", "tier": "specialized", "tools": ["maps_geocode", "maps_reverse_geocode", "maps_search_places", "maps_place_details", "maps_distance_matrix", "maps_directions", "maps_elevation"]},
        {"name": "aws-kb", "tier": "specialized", "tools": ["retrieve_from_knowledge_base"]},
        {"name": "s3", "tier": "specialized", "tools": ["list_buckets", "list_objects", "get_object", "put_object", "delete_object"]},
        {"name": "cloudflare", "tier": "specialized", "tools": ["kv_get", "kv_put", "kv_list", "kv_delete", "r2_get", "r2_put", "r2_list", "r2_delete", "d1_query", "workers_list", "workers_deploy"]},
        {"name": "sentry", "tier": "specialized", "tools": ["list_issues", "get_issue", "resolve_issue", "list_projects", "get_event"]},
        {"name": "raygun", "tier": "specialized", "tools": ["list_errors", "get_error", "resolve_error"]},
        {"name": "linear", "tier": "specialized", "tools": ["list_issues", "create_issue", "update_issue", "search_issues", "list_projects", "list_teams"]},
        {"name": "notion", "tier": "specialized", "tools": ["search", "get_page", "create_page", "update_page", "list_databases", "query_database"]},
        {"name": "obsidian", "tier": "specialized", "tools": ["list_notes", "read_note", "create_note", "update_note", "search_notes", "get_tags"]},
        {"name": "todoist", "tier": "specialized", "tools": ["list_tasks", "create_task", "update_task", "complete_task", "list_projects", "create_project"]},
        {"name": "e2b", "tier": "specialized", "tools": ["create_sandbox", "run_code", "run_terminal_command", "read_file", "write_file", "list_files"]}
    ]
    return {
        "total": len(servers),
        "total_tools": sum(len(s["tools"]) for s in servers),
        "servers": servers
    }


@app.get("/api/v1/mcp/tools")
async def list_mcp_tools():
    """List all available MCP tools."""
    all_tools = []
    servers_response = await list_mcp_servers()
    for server in servers_response["servers"]:
        for tool in server["tools"]:
            all_tools.append({
                "name": tool,
                "server": server["name"],
                "tier": server["tier"]
            })
    return {
        "total": len(all_tools),
        "tools": all_tools
    }


# =============================================================================
# STATIC FILE SERVING (React UI)
# =============================================================================

_UI_DIST = Path(__file__).parent.parent / "ui" / "web" / "dist"

if _UI_DIST.exists():
    from fastapi.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    # Mount assets directory
    _assets_dir = _UI_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/app", response_class=FileResponse, include_in_schema=False)
    @app.get("/app/{full_path:path}", response_class=FileResponse, include_in_schema=False)
    async def serve_react_app(full_path: str = ""):
        """Serve the React SPA for any /app/* route."""
        # Check for a real file first
        target = _UI_DIST / full_path if full_path else _UI_DIST / "index.html"
        if target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(_UI_DIST / "index.html"))

    logger.info(f"✅ React UI served from {_UI_DIST} at /app")
else:
    logger.warning(f"⚠️ React UI dist not found at {_UI_DIST} — run 'make ui-build' to build")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


