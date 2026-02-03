"""
GraphQL types and enums for BAEL API.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

import strawberry


# Enums
@strawberry.enum
class AgentStatus(Enum):
    """Agent status values."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@strawberry.enum
class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@strawberry.enum
class PluginCategory(Enum):
    """Plugin categories."""
    TOOL = "tool"
    REASONING = "reasoning"
    MEMORY = "memory"
    INTEGRATION = "integration"
    PERSONA = "persona"
    WORKFLOW = "workflow"
    MIDDLEWARE = "middleware"
    STORAGE = "storage"


@strawberry.enum
class TaskStatus(Enum):
    """Task execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Types
@strawberry.type
class Agent:
    """An AI agent in the system."""
    id: str
    name: str
    persona: str
    status: AgentStatus
    capabilities: List[str]
    active_tasks: int
    total_tasks_completed: int
    average_response_time: float
    created_at: datetime
    last_active: datetime


@strawberry.type
class Workflow:
    """A workflow definition."""
    id: str
    name: str
    description: str
    version: str
    tasks: List[str]
    dependencies: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime
    execution_count: int
    success_rate: float


@strawberry.type
class WorkflowExecution:
    """A workflow execution instance."""
    id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    progress: float
    current_task: Optional[str]
    result: Optional[strawberry.scalars.JSON]
    error: Optional[str]


@strawberry.type
class Plugin:
    """A plugin in the marketplace."""
    id: str
    name: str
    description: str
    category: PluginCategory
    version: str
    author: str
    downloads: int
    rating: float
    rating_count: int
    installed: bool
    trusted: bool
    created_at: datetime


@strawberry.type
class Task:
    """A task execution."""
    id: str
    type: str
    status: TaskStatus
    agent_id: Optional[str]
    workflow_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    result: Optional[strawberry.scalars.JSON]
    error: Optional[str]


@strawberry.type
class ClusterNode:
    """A cluster node."""
    id: str
    hostname: str
    port: int
    role: str
    status: str
    load: float
    agents_count: int
    tasks_count: int
    last_heartbeat: datetime


@strawberry.type
class ClusterStatus:
    """Overall cluster status."""
    total_nodes: int
    healthy_nodes: int
    leader_node: Optional[str]
    total_agents: int
    total_tasks: int
    average_load: float


@strawberry.type
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    requests_per_minute: int
    active_connections: int
    cache_hit_rate: float
    average_response_time: float
    error_rate: float
    cpu_usage: float
    memory_usage: float


@strawberry.type
class HealthStatus:
    """System health status."""
    status: str
    version: str
    uptime_seconds: float
    components: strawberry.scalars.JSON


@strawberry.type
class AgentEvent:
    """Real-time agent activity event."""
    agent_id: str
    event_type: str
    timestamp: datetime
    data: strawberry.scalars.JSON


@strawberry.type
class ProgressUpdate:
    """Real-time progress update."""
    execution_id: str
    progress: float
    status: str
    current_task: Optional[str]
    timestamp: datetime


# Input types
@strawberry.input
class AgentFilter:
    """Filter for querying agents."""
    status: Optional[AgentStatus] = None
    persona: Optional[str] = None
    search: Optional[str] = None


@strawberry.input
class WorkflowFilter:
    """Filter for querying workflows."""
    status: Optional[WorkflowStatus] = None
    search: Optional[str] = None


@strawberry.input
class PluginFilter:
    """Filter for querying plugins."""
    category: Optional[PluginCategory] = None
    installed: Optional[bool] = None
    search: Optional[str] = None


@strawberry.input
class TimeRange:
    """Time range for metrics."""
    start: datetime
    end: datetime


@strawberry.input
class CreateAgentInput:
    """Input for creating an agent."""
    name: str
    persona: str
    capabilities: Optional[List[str]] = None


@strawberry.input
class CreateWorkflowInput:
    """Input for creating a workflow."""
    name: str
    description: str
    tasks: List[strawberry.scalars.JSON]


@strawberry.input
class ExecuteWorkflowInput:
    """Input for executing a workflow."""
    workflow_id: str
    parameters: Optional[strawberry.scalars.JSON] = None


# Response types
@strawberry.type
class CreateAgentResponse:
    """Response for creating an agent."""
    agent: Agent
    success: bool
    message: str


@strawberry.type
class CreateWorkflowResponse:
    """Response for creating a workflow."""
    workflow: Workflow
    success: bool
    message: str


@strawberry.type
class ExecuteWorkflowResponse:
    """Response for executing a workflow."""
    execution: WorkflowExecution
    success: bool
    message: str


@strawberry.type
class InstallPluginResponse:
    """Response for installing a plugin."""
    plugin: Plugin
    success: bool
    message: str


@strawberry.type
class DeleteResponse:
    """Generic delete response."""
    success: bool
    message: str
