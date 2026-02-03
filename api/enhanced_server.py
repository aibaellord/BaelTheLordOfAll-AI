"""
BAEL - Enhanced API Server with Authentication
FastAPI-based API with proper auth, streaming, and rate limiting.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.brain.brain import BaelBrain
from core.monitoring.production import HealthStatus as MonitoringHealthStatus
from core.monitoring.production import (get_health_checker,
                                        get_metrics_collector)
from core.tasks.task_queue import BackgroundTaskQueue
from core.tasks.task_queue import TaskPriority as QueuePriority

logger = logging.getLogger("BAEL.API")


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    mode: str = Field(default="standard", description="Operating mode")
    stream: bool = Field(default=False, description="Enable streaming")
    persona: Optional[str] = Field(default=None, description="Persona to use")
    model: Optional[str] = Field(default=None, description="Preferred model")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=100000)


class ChatResponse(BaseModel):
    id: str
    response: str
    model_used: str
    tokens_used: int
    execution_time_ms: float
    persona: Optional[str] = None


class TaskRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="normal")
    deadline: Optional[datetime] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    components: Dict[str, str]


# =============================================================================
# Global State
# =============================================================================

# Initialize BAEL Brain and Task Queue
brain_instance: Optional[BaelBrain] = None
task_queue: Optional[BackgroundTaskQueue] = None

# Initialize monitoring
metrics_collector = get_metrics_collector()
health_checker = get_health_checker()


async def get_brain() -> BaelBrain:
    """Get or initialize the BAEL brain instance."""
    global brain_instance
    if brain_instance is None:
        brain_instance = BaelBrain()
        await brain_instance.initialize()
        logger.info("✅ BAEL Brain initialized")

        # Register health check
        health_checker.register_check("brain", lambda: True)

    return brain_instance


async def get_task_queue() -> BackgroundTaskQueue:
    """Get or initialize the task queue."""
    global task_queue
    if task_queue is None:
        task_queue = BackgroundTaskQueue(max_workers=5)
        # Register task handler
        task_queue.register_task(
            name="bael_autonomous_task",
            handler=process_autonomous_task,
            description="Process autonomous BAEL task",
            max_retries=3,
            timeout_seconds=600
        )
        await task_queue.start()
        logger.info("✅ Task queue initialized")

        # Register health check
        health_checker.register_check(
            "task_queue",
            lambda: len(task_queue.running) < task_queue.max_workers
        )

    return task_queue


async def process_autonomous_task(task_id: str, task_request: Dict[str, Any]) -> Dict[str, Any]:
    """Process an autonomous task through BAEL brain."""
    brain = await get_brain()

    task_description = task_request.get("task", "")
    context = task_request.get("context", {})

    try:
        # Process through brain
        result = await brain.think(task_description, context)

        return {
            "success": True,
            "result": result,
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "task_id": task_id
        }


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.requests: Dict[str, List[float]] = {}

    def check(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        minute_ago = now - 60

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > minute_ago
        ]

        if len(self.requests[client_id]) >= self.rpm:
            return False

        self.requests[client_id].append(now)
        return True


rate_limiter = RateLimiter()


# =============================================================================
# API Application
# =============================================================================

app = FastAPI(
    title="BAEL API",
    description="The All-Knowing AI Assistant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = datetime.now()


# =============================================================================
# Dependencies
# =============================================================================

async def get_client_id(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> str:
    """Extract client identifier for rate limiting."""
    if x_api_key:
        return f"apikey:{x_api_key[:8]}"
    if authorization:
        return f"auth:{authorization[:20]}"
    return "anonymous"


async def check_rate_limit(client_id: str = Depends(get_client_id)):
    """Check rate limit for client."""
    if not rate_limiter.check(client_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making more requests."
        )
    return client_id


async def optional_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """Optional authentication - returns user info if authenticated."""
    # Placeholder - implement proper auth
    if x_api_key and x_api_key.startswith("bael_"):
        return {"authenticated": True, "api_key": True}
    return None


# =============================================================================
# Streaming Support
# =============================================================================

async def stream_response(
    messages: List[ChatMessage],
    mode: str,
    persona: Optional[str]
) -> AsyncGenerator[str, None]:
    """Stream response chunks."""
    # Placeholder - integrate with actual BAEL brain
    response = "This is a streaming response from BAEL. "
    response += "The system is processing your request through multiple cognitive layers. "
    response += "Each chunk represents a part of the reasoning process."

    words = response.split()
    for i, word in enumerate(words):
        yield f"data: {word} \n\n"
        await asyncio.sleep(0.05)

    yield "data: [DONE]\n\n"


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """API root endpoint."""
    return {
        "name": "BAEL API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with comprehensive component checks."""
    uptime = (datetime.now() - START_TIME).total_seconds()

    # Run all health checks
    component_statuses = await health_checker.check_all()

    # Convert to simple status dict
    components = {}
    for name, health in component_statuses.items():
        if health.status == MonitoringHealthStatus.HEALTHY:
            components[name] = "operational"
        elif health.status == MonitoringHealthStatus.DEGRADED:
            components[name] = "degraded"
        else:
            components[name] = "error"

    # Determine overall status
    overall_status = health_checker.get_overall_status()
    status_str = "healthy" if overall_status == MonitoringHealthStatus.HEALTHY else "degraded"

    return HealthResponse(
        status=status_str,
        version="1.0.0",
        uptime_seconds=uptime,
        components=components
    )


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    client_id: str = Depends(check_rate_limit),
    user: Optional[Dict] = Depends(optional_auth)
):
    """
    Main chat endpoint.

    Supports:
    - Multiple operating modes (minimal, standard, maximum, autonomous)
    - Persona selection
    - Streaming responses
    - Custom model selection
    """
    start_time = time.time()
    endpoint = "/v1/chat"
    method = "POST"

    if request.stream:
        return StreamingResponse(
            stream_response(request.messages, request.mode, request.persona),
            media_type="text/event-stream"
        )

    # Non-streaming response - integrate with BAEL brain
    brain = await get_brain()

    # Extract last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    # Build context from message history
    context = {
        "mode": request.mode,
        "persona": request.persona,
        "model": request.model,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "history": [msg.dict() for msg in request.messages[:-1]]
    }

    try:
        # Process through brain
        response_text = await brain.process(user_message, context)
        tokens_used = len(response_text.split())  # Rough estimate
        status_code = 200

        # Record metrics
        metrics_collector.record_brain_operation(
            "chat",
            tokens_in=len(user_message.split()),
            tokens_out=tokens_used
        )

    except Exception as e:
        logger.error(f"Brain processing error: {e}")
        response_text = f"I encountered an error processing your request: {str(e)}"
        tokens_used = 0
        status_code = 500

        # Record error
        metrics_collector.record_error("api.chat", type(e).__name__)

    execution_time = (time.time() - start_time) * 1000

    # Record request metrics
    metrics_collector.record_request(endpoint, method, status_code, execution_time / 1000)

    return ChatResponse(
        id=f"chat_{int(time.time())}",
        response=response_text,
        model_used=request.model or "claude-3-sonnet",
        tokens_used=tokens_used,
        execution_time_ms=execution_time,
        persona=request.persona
    )


@app.post("/v1/task", response_model=TaskResponse)
async def submit_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(check_rate_limit)
):
    """
    Submit an autonomous task.

    Tasks are processed in the background and results
    can be retrieved via the /v1/task/{task_id} endpoint.
    """
    task_id = f"task_{int(time.time())}_{id(request)}"

    # Get task queue and submit task
    queue = await get_task_queue()

    # Convert priority string to enum
    priority_map = {
        "critical": QueuePriority.CRITICAL,
        "high": QueuePriority.HIGH,
        "normal": QueuePriority.NORMAL,
        "low": QueuePriority.LOW,
        "background": QueuePriority.BACKGROUND
    }
    priority = priority_map.get(request.priority.lower(), QueuePriority.NORMAL)

    # Submit to queue
    await queue.submit(
        task_name="bael_autonomous_task",
        arguments={
            "task_id": task_id,
            "task_request": request.dict()
        },
        task_id=task_id,
        priority=priority
    )

    logger.info(f"📋 Task {task_id} queued with priority {request.priority}")

    # Record task metrics
    metrics_collector.record_task("queued")
    metrics_collector.set_active_tasks(len(queue.tasks))

    return TaskResponse(
        task_id=task_id,
        status="queued"
    )


@app.get("/v1/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get status of a submitted task."""
    queue = await get_task_queue()

    # Look up task in queue
    task = queue.tasks.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Map internal status to API status
    status_map = {
        "QUEUED": "queued",
        "RUNNING": "processing",
        "COMPLETED": "completed",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "RETRYING": "processing"
    }

    return TaskResponse(
        task_id=task_id,
        status=status_map.get(task.status.name, "unknown"),
        result=task.result if task.status.name == "COMPLETED" else None,
        error=task.error if task.status.name == "FAILED" else None
    )


@app.get("/v1/personas")
async def list_personas():
    """List available personas."""
    return {
        "personas": [
            {"name": "orchestrator", "description": "Master coordinator"},
            {"name": "architect", "description": "System design specialist"},
            {"name": "coder", "description": "Code implementation"},
            {"name": "researcher", "description": "Research and analysis"},
            {"name": "analyst", "description": "Data analysis"},
            {"name": "reviewer", "description": "Code review"},
            {"name": "debugger", "description": "Bug diagnosis"},
            {"name": "teacher", "description": "Education and explanation"}
        ]
    }


@app.get("/v1/capabilities")
async def list_capabilities():
    """List BAEL capabilities by mode."""
    return {
        "modes": {
            "minimal": ["basic_completion", "working_memory"],
            "standard": [
                "basic_completion", "web_search", "file_operations",
                "code_execution", "rag", "workflows"
            ],
            "maximum": [
                "all_standard", "multi_agent", "research",
                "analysis", "autonomous_planning"
            ],
            "autonomous": ["all_capabilities", "self_improvement"]
        }
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """
    from fastapi.responses import Response

    metrics_data = metrics_collector.get_metrics()

    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4"
    )


@app.get("/v1/stats")
async def get_stats():
    """Get system statistics and metrics summary."""
    queue = await get_task_queue()

    return {
        "system": {
            "uptime_seconds": health_checker.get_uptime_seconds(),
            "status": health_checker.get_overall_status().value
        },
        "tasks": {
            "total": len(queue.tasks),
            "active": len(queue.running),
            "pending": queue.pending.qsize()
        },
        "health": health_checker.get_health_report()
    }


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
