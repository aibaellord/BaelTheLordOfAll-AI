#!/usr/bin/env python3
"""
BAEL - Agent Orchestrator
Advanced multi-agent coordination and execution system.

Features:
- Agent lifecycle management
- Task distribution and scheduling
- Inter-agent communication
- Tool/capability registration
- Memory and context sharing
- Hierarchical agent structures
- Parallel and sequential execution
- Agent state management
- Event-driven coordination
- Performance monitoring
"""

import asyncio
import heapq
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
TContext = TypeVar('TContext')


# =============================================================================
# ENUMS
# =============================================================================

class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    ERROR = "error"
    TERMINATED = "terminated"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageType(Enum):
    """Inter-agent message types."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"
    BROADCAST = "broadcast"


class AgentRole(Enum):
    """Agent roles in the system."""
    WORKER = "worker"
    SUPERVISOR = "supervisor"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AgentConfig:
    """Configuration for an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Agent"
    role: AgentRole = AgentRole.WORKER
    capabilities: Set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 5
    timeout: float = 30.0
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    input_data: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: Set[str] = field(default_factory=set)
    deadline: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __lt__(self, other: 'Task') -> bool:
        return self.priority.value > other.priority.value


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    agent_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Inter-agent message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None for broadcast
    content: Any = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    """Current state of an agent."""
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    last_active: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Memory:
    """Agent memory entry."""
    key: str
    value: Any
    scope: str = "local"  # local, shared, persistent
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# =============================================================================
# TOOLS
# =============================================================================

@dataclass
class Tool:
    """A tool available to agents."""
    name: str
    description: str
    handler: Callable[..., Awaitable[Any]]
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: Set[str] = field(default_factory=set)


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)

    def list(self) -> List[str]:
        """List all tools."""
        return list(self._tools.keys())

    async def invoke(self, name: str, **kwargs) -> Any:
        """Invoke a tool."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        # Validate required parameters
        missing = tool.required_params - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        return await tool.handler(**kwargs)


# =============================================================================
# BASE AGENT
# =============================================================================

class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = AgentState(agent_id=config.id)
        self._memory: Dict[str, Memory] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._running = False

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task."""
        pass

    async def start(self) -> None:
        """Start the agent."""
        self._running = True
        self.state.status = AgentStatus.IDLE

    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False
        self.state.status = AgentStatus.TERMINATED

    async def pause(self) -> None:
        """Pause the agent."""
        self.state.status = AgentStatus.PAUSED

    async def resume(self) -> None:
        """Resume the agent."""
        if self.state.status == AgentStatus.PAUSED:
            self.state.status = AgentStatus.IDLE

    # Memory operations
    def remember(self, key: str, value: Any, scope: str = "local") -> None:
        """Store in memory."""
        self._memory[key] = Memory(key=key, value=value, scope=scope)

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve from memory."""
        mem = self._memory.get(key)
        return mem.value if mem else None

    def forget(self, key: str) -> None:
        """Remove from memory."""
        if key in self._memory:
            del self._memory[key]

    # Message handling
    def on_message(self, msg_type: MessageType, handler: Callable) -> None:
        """Register message handler."""
        self._message_handlers[msg_type].append(handler)

    async def receive_message(self, message: Message) -> None:
        """Receive and process a message."""
        handlers = self._message_handlers.get(message.type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")

    async def send_message(self, orchestrator: 'AgentOrchestrator', message: Message) -> None:
        """Send a message through the orchestrator."""
        message.sender_id = self.id
        await orchestrator.route_message(message)


# =============================================================================
# CONCRETE AGENTS
# =============================================================================

class WorkerAgent(BaseAgent):
    """Basic worker agent."""

    def __init__(self, config: AgentConfig, tools: Optional[ToolRegistry] = None):
        super().__init__(config)
        self.tools = tools or ToolRegistry()

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task."""
        started = datetime.utcnow()
        self.state.status = AgentStatus.RUNNING
        self.state.current_tasks.append(task.id)

        try:
            # Simple task execution - subclasses can override
            output = await self._process_task(task)

            completed = datetime.utcnow()
            execution_time = (completed - started).total_seconds()

            self.state.completed_tasks += 1
            self.state.total_execution_time += execution_time

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output=output,
                agent_id=self.id,
                started_at=started,
                completed_at=completed,
                execution_time=execution_time
            )

        except Exception as e:
            self.state.failed_tasks += 1
            self.state.error_message = str(e)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                agent_id=self.id,
                started_at=started,
                completed_at=datetime.utcnow()
            )

        finally:
            self.state.current_tasks.remove(task.id)
            self.state.status = AgentStatus.IDLE
            self.state.last_active = datetime.utcnow()

    async def _process_task(self, task: Task) -> Any:
        """Process task - override in subclasses."""
        # Simulate work
        await asyncio.sleep(0.1)
        return {"task": task.name, "processed": True}


class SupervisorAgent(BaseAgent):
    """Supervisor that coordinates worker agents."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._workers: Dict[str, BaseAgent] = {}
        self._task_assignments: Dict[str, str] = {}  # task_id -> agent_id

    def add_worker(self, agent: BaseAgent) -> None:
        """Add a worker agent."""
        self._workers[agent.id] = agent

    def remove_worker(self, agent_id: str) -> None:
        """Remove a worker agent."""
        if agent_id in self._workers:
            del self._workers[agent_id]

    def get_available_worker(self, task: Task) -> Optional[BaseAgent]:
        """Find available worker for task."""
        for agent in self._workers.values():
            if agent.state.status == AgentStatus.IDLE:
                # Check capabilities
                if task.required_capabilities.issubset(agent.config.capabilities):
                    # Check capacity
                    if len(agent.state.current_tasks) < agent.config.max_concurrent_tasks:
                        return agent
        return None

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute task by delegating to workers."""
        worker = self.get_available_worker(task)

        if not worker:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="No available worker"
            )

        self._task_assignments[task.id] = worker.id

        try:
            result = await worker.execute_task(task)
            return result
        finally:
            del self._task_assignments[task.id]


# =============================================================================
# MESSAGE BUS
# =============================================================================

class MessageBus:
    """Message bus for inter-agent communication."""

    def __init__(self):
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = {}

    def subscribe(self, agent_id: str, handler: Callable[[Message], Awaitable[None]]) -> None:
        """Subscribe to messages."""
        self._subscriptions[agent_id].append(handler)
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()

    def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe from messages."""
        if agent_id in self._subscriptions:
            del self._subscriptions[agent_id]
        if agent_id in self._queues:
            del self._queues[agent_id]

    async def send(self, message: Message) -> None:
        """Send a message."""
        if message.recipient_id:
            # Direct message
            handlers = self._subscriptions.get(message.recipient_id, [])
            for handler in handlers:
                await handler(message)
        elif message.type == MessageType.BROADCAST:
            # Broadcast
            for agent_id, handlers in self._subscriptions.items():
                if agent_id != message.sender_id:
                    for handler in handlers:
                        await handler(message)

    async def broadcast(self, sender_id: str, content: Any) -> None:
        """Broadcast a message to all agents."""
        message = Message(
            type=MessageType.BROADCAST,
            sender_id=sender_id,
            content=content
        )
        await self.send(message)


# =============================================================================
# TASK QUEUE
# =============================================================================

class TaskQueue:
    """Priority queue for tasks."""

    def __init__(self):
        self._queue: List[Tuple[int, Task]] = []
        self._pending: Dict[str, Task] = {}

    def push(self, task: Task) -> None:
        """Add task to queue."""
        priority = -task.priority.value  # Negative for max-heap behavior
        heapq.heappush(self._queue, (priority, task))
        self._pending[task.id] = task

    def pop(self) -> Optional[Task]:
        """Get highest priority task."""
        while self._queue:
            _, task = heapq.heappop(self._queue)
            if task.id in self._pending:
                del self._pending[task.id]
                return task
        return None

    def peek(self) -> Optional[Task]:
        """Peek at highest priority task."""
        while self._queue:
            priority, task = self._queue[0]
            if task.id in self._pending:
                return task
            heapq.heappop(self._queue)
        return None

    def remove(self, task_id: str) -> bool:
        """Remove task from queue."""
        if task_id in self._pending:
            del self._pending[task_id]
            return True
        return False

    def size(self) -> int:
        """Get queue size."""
        return len(self._pending)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._pending) == 0


# =============================================================================
# AGENT ORCHESTRATOR
# =============================================================================

class AgentOrchestrator:
    """
    Agent Orchestrator for BAEL.

    Coordinates multiple agents, manages task distribution,
    and handles inter-agent communication.
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._task_queue = TaskQueue()
        self._message_bus = MessageBus()
        self._tool_registry = ToolRegistry()
        self._results: Dict[str, TaskResult] = {}
        self._shared_memory: Dict[str, Memory] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Event callbacks
        self._on_task_completed: List[Callable[[TaskResult], Awaitable[None]]] = []
        self._on_agent_error: List[Callable[[str, str], Awaitable[None]]] = []

    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.id] = agent
        self._message_bus.subscribe(agent.id, agent.receive_message)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._message_bus.unsubscribe(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentConfig]:
        """List all agents."""
        return [a.config for a in self._agents.values()]

    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state."""
        agent = self._agents.get(agent_id)
        return agent.state if agent else None

    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------

    async def submit_task(self, task: Task) -> str:
        """Submit a task for execution."""
        self._task_queue.push(task)
        logger.info(f"Task submitted: {task.id}")
        return task.id

    async def submit_tasks(self, tasks: List[Task]) -> List[str]:
        """Submit multiple tasks."""
        return [await self.submit_task(t) for t in tasks]

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result."""
        return self._results.get(task_id)

    async def wait_for_task(self, task_id: str, timeout: float = 30.0) -> TaskResult:
        """Wait for task completion."""
        start = datetime.utcnow()

        while True:
            result = self._results.get(task_id)
            if result:
                return result

            elapsed = (datetime.utcnow() - start).total_seconds()
            if elapsed > timeout:
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error="Timeout waiting for task"
                )

            await asyncio.sleep(0.1)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        return self._task_queue.remove(task_id)

    # -------------------------------------------------------------------------
    # SCHEDULING
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the orchestrator."""
        self._running = True

        # Start all agents
        for agent in self._agents.values():
            await agent.start()

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Stop all agents
        for agent in self._agents.values():
            await agent.stop()

    async def _scheduler_loop(self) -> None:
        """Main scheduling loop."""
        while self._running:
            if not self._task_queue.is_empty():
                await self._schedule_tasks()
            await asyncio.sleep(0.01)

    async def _schedule_tasks(self) -> None:
        """Schedule pending tasks to available agents."""
        task = self._task_queue.peek()

        if not task:
            return

        # Find suitable agent
        agent = self._find_agent_for_task(task)

        if agent:
            self._task_queue.pop()
            asyncio.create_task(self._execute_task_on_agent(task, agent))

    def _find_agent_for_task(self, task: Task) -> Optional[BaseAgent]:
        """Find suitable agent for task."""
        for agent in self._agents.values():
            if agent.state.status not in [AgentStatus.IDLE, AgentStatus.WAITING]:
                continue

            # Check capabilities
            if task.required_capabilities:
                if not task.required_capabilities.issubset(agent.config.capabilities):
                    continue

            # Check capacity
            if len(agent.state.current_tasks) >= agent.config.max_concurrent_tasks:
                continue

            return agent

        return None

    async def _execute_task_on_agent(self, task: Task, agent: BaseAgent) -> None:
        """Execute task on agent."""
        try:
            result = await asyncio.wait_for(
                agent.execute_task(task),
                timeout=agent.config.timeout
            )
        except asyncio.TimeoutError:
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="Task timed out",
                agent_id=agent.id
            )
        except Exception as e:
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                agent_id=agent.id
            )

        self._results[task.id] = result

        # Notify callbacks
        for callback in self._on_task_completed:
            try:
                await callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # -------------------------------------------------------------------------
    # MESSAGING
    # -------------------------------------------------------------------------

    async def route_message(self, message: Message) -> None:
        """Route a message."""
        await self._message_bus.send(message)

    async def broadcast(self, sender_id: str, content: Any) -> None:
        """Broadcast message to all agents."""
        await self._message_bus.broadcast(sender_id, content)

    # -------------------------------------------------------------------------
    # TOOLS
    # -------------------------------------------------------------------------

    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        self._tool_registry.register(tool)

    def list_tools(self) -> List[str]:
        """List available tools."""
        return self._tool_registry.list()

    async def invoke_tool(self, name: str, **kwargs) -> Any:
        """Invoke a tool."""
        return await self._tool_registry.invoke(name, **kwargs)

    # -------------------------------------------------------------------------
    # SHARED MEMORY
    # -------------------------------------------------------------------------

    def set_shared(self, key: str, value: Any) -> None:
        """Set shared memory value."""
        self._shared_memory[key] = Memory(key=key, value=value, scope="shared")

    def get_shared(self, key: str) -> Optional[Any]:
        """Get shared memory value."""
        mem = self._shared_memory.get(key)
        return mem.value if mem else None

    def delete_shared(self, key: str) -> None:
        """Delete shared memory value."""
        if key in self._shared_memory:
            del self._shared_memory[key]

    # -------------------------------------------------------------------------
    # EVENTS
    # -------------------------------------------------------------------------

    def on_task_completed(self, callback: Callable[[TaskResult], Awaitable[None]]) -> None:
        """Register task completion callback."""
        self._on_task_completed.append(callback)

    def on_agent_error(self, callback: Callable[[str, str], Awaitable[None]]) -> None:
        """Register agent error callback."""
        self._on_agent_error.append(callback)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        total_completed = sum(a.state.completed_tasks for a in self._agents.values())
        total_failed = sum(a.state.failed_tasks for a in self._agents.values())

        return {
            "agents": len(self._agents),
            "pending_tasks": self._task_queue.size(),
            "completed_tasks": total_completed,
            "failed_tasks": total_failed,
            "agents_idle": sum(1 for a in self._agents.values() if a.state.status == AgentStatus.IDLE),
            "agents_busy": sum(1 for a in self._agents.values() if a.state.status == AgentStatus.RUNNING),
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Agent Orchestrator."""
    print("=" * 70)
    print("BAEL - AGENT ORCHESTRATOR DEMO")
    print("Multi-Agent Coordination System")
    print("=" * 70)
    print()

    orchestrator = AgentOrchestrator()

    # 1. Create Agents
    print("1. CREATE AGENTS:")
    print("-" * 40)

    agents = [
        WorkerAgent(AgentConfig(
            name="Worker-1",
            role=AgentRole.WORKER,
            capabilities={"processing", "analysis"}
        )),
        WorkerAgent(AgentConfig(
            name="Worker-2",
            role=AgentRole.WORKER,
            capabilities={"processing", "reporting"}
        )),
        WorkerAgent(AgentConfig(
            name="Specialist",
            role=AgentRole.SPECIALIST,
            capabilities={"ml", "prediction"}
        )),
    ]

    for agent in agents:
        orchestrator.register_agent(agent)
        print(f"   Registered: {agent.name} ({agent.config.role.value})")

    print()

    # 2. Register Tools
    print("2. REGISTER TOOLS:")
    print("-" * 40)

    async def analyze_data(data: Dict) -> Dict:
        return {"analysis": "complete", "input": data}

    async def generate_report(title: str) -> str:
        return f"Report: {title}"

    orchestrator.register_tool(Tool(
        name="analyze",
        description="Analyze data",
        handler=analyze_data,
        required_params={"data"}
    ))

    orchestrator.register_tool(Tool(
        name="report",
        description="Generate report",
        handler=generate_report,
        required_params={"title"}
    ))

    print(f"   Tools: {orchestrator.list_tools()}")
    print()

    # 3. Start Orchestrator
    print("3. START ORCHESTRATOR:")
    print("-" * 40)

    await orchestrator.start()
    print("   Orchestrator started")
    print()

    # 4. Submit Tasks
    print("4. SUBMIT TASKS:")
    print("-" * 40)

    tasks = [
        Task(
            name="Data Analysis",
            priority=TaskPriority.HIGH,
            required_capabilities={"processing"},
            input_data={"type": "analysis"}
        ),
        Task(
            name="Generate Report",
            priority=TaskPriority.NORMAL,
            required_capabilities={"reporting"},
            input_data={"type": "report"}
        ),
        Task(
            name="ML Prediction",
            priority=TaskPriority.CRITICAL,
            required_capabilities={"ml"},
            input_data={"type": "prediction"}
        ),
    ]

    task_ids = await orchestrator.submit_tasks(tasks)
    for t, tid in zip(tasks, task_ids):
        print(f"   Submitted: {t.name} (priority: {t.priority.name})")

    print()

    # 5. Wait for Results
    print("5. WAIT FOR RESULTS:")
    print("-" * 40)

    for task_id in task_ids:
        result = await orchestrator.wait_for_task(task_id, timeout=5.0)
        status = "✓" if result.status == TaskStatus.COMPLETED else "✗"
        print(f"   {status} Task {task_id[:8]}... - {result.status.value}")

    print()

    # 6. Agent States
    print("6. AGENT STATES:")
    print("-" * 40)

    for agent in agents:
        state = orchestrator.get_agent_state(agent.id)
        print(f"   {agent.name}:")
        print(f"      Status: {state.status.value}")
        print(f"      Completed: {state.completed_tasks}")
        print(f"      Failed: {state.failed_tasks}")

    print()

    # 7. Shared Memory
    print("7. SHARED MEMORY:")
    print("-" * 40)

    orchestrator.set_shared("config", {"version": "1.0"})
    orchestrator.set_shared("counter", 42)

    print(f"   config: {orchestrator.get_shared('config')}")
    print(f"   counter: {orchestrator.get_shared('counter')}")
    print()

    # 8. Tool Invocation
    print("8. TOOL INVOCATION:")
    print("-" * 40)

    result = await orchestrator.invoke_tool("analyze", data={"sample": True})
    print(f"   analyze: {result}")

    result = await orchestrator.invoke_tool("report", title="Monthly Summary")
    print(f"   report: {result}")
    print()

    # 9. Messaging
    print("9. INTER-AGENT MESSAGING:")
    print("-" * 40)

    received = []

    async def message_handler(msg: Message):
        received.append(msg)

    for agent in agents:
        agent.on_message(MessageType.BROADCAST, message_handler)

    await orchestrator.broadcast("system", {"event": "status_update"})
    await asyncio.sleep(0.1)  # Allow messages to process

    print(f"   Broadcast sent, {len(received)} agents received")
    print()

    # 10. Event Callbacks
    print("10. EVENT CALLBACKS:")
    print("-" * 40)

    completed_events = []

    async def on_complete(result: TaskResult):
        completed_events.append(result.task_id)

    orchestrator.on_task_completed(on_complete)

    # Submit another task
    task = Task(name="Callback Test", required_capabilities={"processing"})
    await orchestrator.submit_task(task)
    await orchestrator.wait_for_task(task.id)

    print(f"   Callback received: {len(completed_events)} events")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = orchestrator.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 12. Cleanup
    print("12. STOP ORCHESTRATOR:")
    print("-" * 40)

    await orchestrator.stop()
    print("   Orchestrator stopped")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Agent Orchestrator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
