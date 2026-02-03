"""
BAEL - Admin Dashboard API
REST API endpoints for admin dashboard.

Features:
- System monitoring
- Agent management
- Task management
- Analytics endpoints
- User management
- Configuration API
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Union

try:
    from fastapi import (BackgroundTasks, Body, Depends, FastAPI,
                         HTTPException, Query)
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for type hints
    FastAPI = None
    BaseModel = object

logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AgentCreate(BaseModel):
    """Create agent request."""
    name: str = Field(..., description="Agent name")
    persona: str = Field(default="default", description="Persona to use")
    model: str = Field(default="gpt-4", description="Model to use")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")


class AgentUpdate(BaseModel):
    """Update agent request."""
    name: Optional[str] = None
    persona: Optional[str] = None
    model: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class TaskCreate(BaseModel):
    """Create task request."""
    name: str = Field(..., description="Task name")
    description: str = Field(default="", description="Task description")
    agent_id: Optional[str] = Field(None, description="Assigned agent")
    priority: int = Field(default=1, ge=1, le=5, description="Priority 1-5")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    """Update task request."""
    name: Optional[str] = None
    description: Optional[str] = None
    agent_id: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    key: str
    value: Any
    section: str = "general"


class UserCreate(BaseModel):
    """Create user request."""
    username: str
    email: str
    password: str
    role: str = "user"


class ChatMessage(BaseModel):
    """Chat message request."""
    message: str
    agent_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# MOCK DATA STORE
# =============================================================================

class DataStore:
    """In-memory data store for demo."""

    def __init__(self):
        self.agents: Dict[str, Dict] = {}
        self.tasks: Dict[str, Dict] = {}
        self.users: Dict[str, Dict] = {}
        self.metrics: List[Dict] = []
        self.logs: List[Dict] = []
        self.config: Dict[str, Dict] = {}

        self._init_sample_data()

    def _init_sample_data(self):
        """Initialize sample data."""
        # Sample agents
        self.agents = {
            "agent-001": {
                "id": "agent-001",
                "name": "Atlas",
                "persona": "architect",
                "model": "gpt-4",
                "status": "active",
                "tasks_completed": 42,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            },
            "agent-002": {
                "id": "agent-002",
                "name": "Nova",
                "persona": "coder",
                "model": "claude-3-opus",
                "status": "active",
                "tasks_completed": 128,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            },
            "agent-003": {
                "id": "agent-003",
                "name": "Sage",
                "persona": "researcher",
                "model": "gpt-4-turbo",
                "status": "idle",
                "tasks_completed": 67,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        }

        # Sample tasks
        self.tasks = {
            "task-001": {
                "id": "task-001",
                "name": "Code Review",
                "description": "Review pull request #42",
                "agent_id": "agent-002",
                "status": "in_progress",
                "priority": 2,
                "created_at": datetime.now().isoformat(),
                "progress": 65
            },
            "task-002": {
                "id": "task-002",
                "name": "Research Paper Analysis",
                "description": "Analyze recent ML papers",
                "agent_id": "agent-003",
                "status": "completed",
                "priority": 1,
                "created_at": datetime.now().isoformat(),
                "progress": 100
            },
            "task-003": {
                "id": "task-003",
                "name": "System Architecture",
                "description": "Design microservices architecture",
                "agent_id": "agent-001",
                "status": "pending",
                "priority": 3,
                "created_at": datetime.now().isoformat(),
                "progress": 0
            }
        }

        # Sample config
        self.config = {
            "general": {
                "debug_mode": False,
                "log_level": "info",
                "max_agents": 10
            },
            "models": {
                "default_model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096
            },
            "security": {
                "require_auth": True,
                "session_timeout": 3600,
                "rate_limit": 100
            }
        }


# Global data store
store = DataStore()


# =============================================================================
# FASTAPI APP
# =============================================================================

def create_admin_app() -> "FastAPI":
    """Create admin dashboard API."""
    if FastAPI is None:
        raise ImportError("FastAPI not installed")

    app = FastAPI(
        title="BAEL Admin Dashboard API",
        description="Administration API for BAEL AI Agent System",
        version="1.0.0"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # ==========================================================================
    # SYSTEM ENDPOINTS
    # ==========================================================================

    @app.get("/api/system/status")
    async def get_system_status():
        """Get system status."""
        import platform

        return {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": time.time(),
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "agents": {
                "total": len(store.agents),
                "active": sum(1 for a in store.agents.values() if a["status"] == "active"),
                "idle": sum(1 for a in store.agents.values() if a["status"] == "idle")
            },
            "tasks": {
                "total": len(store.tasks),
                "pending": sum(1 for t in store.tasks.values() if t["status"] == "pending"),
                "in_progress": sum(1 for t in store.tasks.values() if t["status"] == "in_progress"),
                "completed": sum(1 for t in store.tasks.values() if t["status"] == "completed")
            }
        }

    @app.get("/api/system/metrics")
    async def get_system_metrics():
        """Get system metrics."""
        return {
            "cpu_usage": 45.2,
            "memory_usage": 62.5,
            "disk_usage": 38.7,
            "network_in": 1024000,
            "network_out": 512000,
            "requests_per_minute": 127,
            "avg_response_time_ms": 45,
            "error_rate": 0.02,
            "active_connections": 15,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/system/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "timestamp": datetime.now().isoformat()}

    # ==========================================================================
    # AGENT ENDPOINTS
    # ==========================================================================

    @app.get("/api/agents")
    async def list_agents(
        status: Optional[str] = Query(None, description="Filter by status"),
        persona: Optional[str] = Query(None, description="Filter by persona"),
        limit: int = Query(100, le=1000),
        offset: int = Query(0, ge=0)
    ):
        """List all agents."""
        agents = list(store.agents.values())

        if status:
            agents = [a for a in agents if a["status"] == status]
        if persona:
            agents = [a for a in agents if a["persona"] == persona]

        return {
            "total": len(agents),
            "agents": agents[offset:offset + limit]
        }

    @app.get("/api/agents/{agent_id}")
    async def get_agent(agent_id: str):
        """Get agent by ID."""
        if agent_id not in store.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        return store.agents[agent_id]

    @app.post("/api/agents")
    async def create_agent(agent: AgentCreate):
        """Create new agent."""
        agent_id = f"agent-{len(store.agents) + 1:03d}"

        store.agents[agent_id] = {
            "id": agent_id,
            "name": agent.name,
            "persona": agent.persona,
            "model": agent.model,
            "config": agent.config,
            "status": "idle",
            "tasks_completed": 0,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }

        return store.agents[agent_id]

    @app.patch("/api/agents/{agent_id}")
    async def update_agent(agent_id: str, update: AgentUpdate):
        """Update agent."""
        if agent_id not in store.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent = store.agents[agent_id]

        if update.name:
            agent["name"] = update.name
        if update.persona:
            agent["persona"] = update.persona
        if update.model:
            agent["model"] = update.model
        if update.config:
            agent["config"] = update.config
        if update.status:
            agent["status"] = update.status

        agent["last_active"] = datetime.now().isoformat()

        return agent

    @app.delete("/api/agents/{agent_id}")
    async def delete_agent(agent_id: str):
        """Delete agent."""
        if agent_id not in store.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        del store.agents[agent_id]
        return {"status": "deleted", "id": agent_id}

    @app.post("/api/agents/{agent_id}/start")
    async def start_agent(agent_id: str):
        """Start agent."""
        if agent_id not in store.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        store.agents[agent_id]["status"] = "active"
        store.agents[agent_id]["last_active"] = datetime.now().isoformat()

        return {"status": "started", "agent": store.agents[agent_id]}

    @app.post("/api/agents/{agent_id}/stop")
    async def stop_agent(agent_id: str):
        """Stop agent."""
        if agent_id not in store.agents:
            raise HTTPException(status_code=404, detail="Agent not found")

        store.agents[agent_id]["status"] = "idle"

        return {"status": "stopped", "agent": store.agents[agent_id]}

    # ==========================================================================
    # TASK ENDPOINTS
    # ==========================================================================

    @app.get("/api/tasks")
    async def list_tasks(
        status: Optional[str] = Query(None),
        agent_id: Optional[str] = Query(None),
        priority: Optional[int] = Query(None, ge=1, le=5),
        limit: int = Query(100, le=1000),
        offset: int = Query(0, ge=0)
    ):
        """List all tasks."""
        tasks = list(store.tasks.values())

        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if agent_id:
            tasks = [t for t in tasks if t.get("agent_id") == agent_id]
        if priority:
            tasks = [t for t in tasks if t["priority"] == priority]

        return {
            "total": len(tasks),
            "tasks": tasks[offset:offset + limit]
        }

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get task by ID."""
        if task_id not in store.tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        return store.tasks[task_id]

    @app.post("/api/tasks")
    async def create_task(task: TaskCreate):
        """Create new task."""
        task_id = f"task-{len(store.tasks) + 1:03d}"

        store.tasks[task_id] = {
            "id": task_id,
            "name": task.name,
            "description": task.description,
            "agent_id": task.agent_id,
            "priority": task.priority,
            "metadata": task.metadata,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }

        return store.tasks[task_id]

    @app.patch("/api/tasks/{task_id}")
    async def update_task(task_id: str, update: TaskUpdate):
        """Update task."""
        if task_id not in store.tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        task = store.tasks[task_id]

        if update.name:
            task["name"] = update.name
        if update.description:
            task["description"] = update.description
        if update.agent_id:
            task["agent_id"] = update.agent_id
        if update.priority:
            task["priority"] = update.priority
        if update.status:
            task["status"] = update.status
        if update.result:
            task["result"] = update.result

        return task

    @app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: str):
        """Delete task."""
        if task_id not in store.tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        del store.tasks[task_id]
        return {"status": "deleted", "id": task_id}

    # ==========================================================================
    # ANALYTICS ENDPOINTS
    # ==========================================================================

    @app.get("/api/analytics/overview")
    async def get_analytics_overview():
        """Get analytics overview."""
        return {
            "period": "last_7_days",
            "agents": {
                "total": len(store.agents),
                "new": 2,
                "active_today": 3
            },
            "tasks": {
                "total": len(store.tasks),
                "completed_today": 12,
                "avg_completion_time_hours": 2.5
            },
            "messages": {
                "total": 1547,
                "today": 234
            },
            "api_calls": {
                "total": 25680,
                "today": 3412,
                "avg_latency_ms": 45
            },
            "costs": {
                "total_usd": 156.78,
                "today_usd": 23.45,
                "by_model": {
                    "gpt-4": 89.50,
                    "claude-3-opus": 45.20,
                    "gpt-4-turbo": 22.08
                }
            }
        }

    @app.get("/api/analytics/usage")
    async def get_usage_analytics(
        period: str = Query("7d", regex="^(1d|7d|30d|90d)$")
    ):
        """Get usage analytics."""
        # Generate sample data points
        points = []
        days = int(period[:-1])

        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            points.append({
                "date": date.strftime("%Y-%m-%d"),
                "api_calls": 2500 + (i * 100),
                "tokens_used": 125000 + (i * 5000),
                "cost_usd": 15.50 + (i * 1.5),
                "tasks_completed": 10 + i,
                "avg_response_time_ms": 42 + (i % 10)
            })

        return {
            "period": period,
            "data_points": points
        }

    @app.get("/api/analytics/agents")
    async def get_agent_analytics():
        """Get agent performance analytics."""
        agent_stats = []

        for agent_id, agent in store.agents.items():
            agent_stats.append({
                "id": agent_id,
                "name": agent["name"],
                "persona": agent["persona"],
                "tasks_completed": agent["tasks_completed"],
                "avg_task_time_minutes": 15.5,
                "success_rate": 0.95,
                "tokens_used": 45000,
                "cost_usd": 12.50
            })

        return {
            "agents": agent_stats,
            "top_performer": agent_stats[1] if len(agent_stats) > 1 else None
        }

    # ==========================================================================
    # CONFIGURATION ENDPOINTS
    # ==========================================================================

    @app.get("/api/config")
    async def get_config():
        """Get all configuration."""
        return store.config

    @app.get("/api/config/{section}")
    async def get_config_section(section: str):
        """Get configuration section."""
        if section not in store.config:
            raise HTTPException(status_code=404, detail="Section not found")

        return store.config[section]

    @app.patch("/api/config")
    async def update_config(update: ConfigUpdate):
        """Update configuration."""
        if update.section not in store.config:
            store.config[update.section] = {}

        store.config[update.section][update.key] = update.value

        return {
            "status": "updated",
            "section": update.section,
            "key": update.key,
            "value": update.value
        }

    # ==========================================================================
    # CHAT ENDPOINTS
    # ==========================================================================

    @app.post("/api/chat")
    async def chat(message: ChatMessage):
        """Send chat message to agent."""
        # Mock response
        return {
            "id": f"msg-{int(time.time())}",
            "response": f"I received your message: '{message.message}'. This is a demo response from BAEL.",
            "agent_id": message.agent_id or "agent-001",
            "tokens_used": 150,
            "timestamp": datetime.now().isoformat()
        }

    @app.get("/api/chat/history")
    async def get_chat_history(
        agent_id: Optional[str] = None,
        limit: int = Query(50, le=200)
    ):
        """Get chat history."""
        # Mock history
        return {
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": "Hello BAEL",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": "msg-2",
                    "role": "assistant",
                    "content": "Hello! I am BAEL, the Lord of All AI Agents. How can I assist you?",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }

    # ==========================================================================
    # LOGS ENDPOINTS
    # ==========================================================================

    @app.get("/api/logs")
    async def get_logs(
        level: Optional[str] = Query(None, regex="^(debug|info|warning|error)$"),
        source: Optional[str] = None,
        limit: int = Query(100, le=1000)
    ):
        """Get system logs."""
        # Mock logs
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "source": "agent-001",
                "message": "Task completed successfully"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "debug",
                "source": "system",
                "message": "Health check passed"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "warning",
                "source": "agent-002",
                "message": "Rate limit approaching"
            }
        ]

        if level:
            logs = [l for l in logs if l["level"] == level]
        if source:
            logs = [l for l in logs if l["source"] == source]

        return {"logs": logs[:limit]}

    # ==========================================================================
    # WEBSOCKET FOR REAL-TIME UPDATES
    # ==========================================================================

    from fastapi import WebSocket, WebSocketDisconnect

    class ConnectionManager:
        def __init__(self):
            self.active_connections: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            self.active_connections.remove(websocket)

        async def broadcast(self, message: dict):
            for connection in self.active_connections:
                await connection.send_json(message)

    ws_manager = ConnectionManager()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()

                # Handle different message types
                msg_type = data.get("type", "ping")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "subscribe":
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": data.get("channel", "default")
                    })
                elif msg_type == "chat":
                    # Process chat message
                    response = {
                        "type": "response",
                        "content": f"Received: {data.get('message', '')}",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_json(response)

        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app


# =============================================================================
# STANDALONE RUN
# =============================================================================

def run_admin_server(host: str = "0.0.0.0", port: int = 8080):
    """Run admin server."""
    import uvicorn

    app = create_admin_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("=== BAEL Admin Dashboard API ===")
    print("Starting server on http://localhost:8080")
    print("\nEndpoints:")
    print("  GET  /api/system/status   - System status")
    print("  GET  /api/agents          - List agents")
    print("  POST /api/agents          - Create agent")
    print("  GET  /api/tasks           - List tasks")
    print("  POST /api/tasks           - Create task")
    print("  GET  /api/analytics/overview - Analytics")
    print("  GET  /api/config          - Configuration")
    print("  POST /api/chat            - Chat with agent")
    print("  WS   /ws                  - WebSocket")
    print("\nPress Ctrl+C to stop")

    run_admin_server()
