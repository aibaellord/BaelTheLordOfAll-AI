#!/usr/bin/env python3
"""
BAEL - Agent Coordinator
Comprehensive agent lifecycle management and coordination.

This module manages the entire lifecycle of AI agents,
including spawning, scheduling, communication, and termination.

Features:
- Agent lifecycle management
- Agent pool management
- Work distribution
- Inter-agent communication
- Agent health monitoring
- Load balancing
- Agent scaling
- Capability matching
- Task assignment
- Agent clustering
"""

import asyncio
import heapq
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple,
                    Type, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentType(Enum):
    """Types of agents."""
    WORKER = "worker"           # General purpose
    SPECIALIST = "specialist"   # Domain expert
    SUPERVISOR = "supervisor"   # Manages other agents
    COORDINATOR = "coordinator" # Orchestrates workflows
    MONITOR = "monitor"         # Health/performance monitoring
    GATEWAY = "gateway"         # External interface


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    WEIGHTED = "weighted"
    CAPABILITY_BASED = "capability_based"


class ScalingMode(Enum):
    """Agent scaling modes."""
    MANUAL = "manual"
    AUTO = "auto"
    PREDICTIVE = "predictive"


class MessageType(Enum):
    """Inter-agent message types."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    COMMAND = "command"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Capability:
    """An agent capability."""
    name: str
    level: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Agent configuration."""
    type: AgentType = AgentType.WORKER
    capabilities: List[Capability] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    timeout_seconds: float = 300.0
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Agent performance metrics."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    average_response_time: float = 0.0
    current_load: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0

    def update_completion(self, success: bool, duration: float) -> None:
        """Update metrics after task completion."""
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1

        self.total_processing_time += duration
        total = self.tasks_completed + self.tasks_failed
        self.average_response_time = self.total_processing_time / total
        self.last_activity = datetime.now()


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    assigned_agent: Optional[str] = None

    def __lt__(self, other):
        """Compare by priority for heap."""
        return self.priority.value < other.priority.value


@dataclass
class Message:
    """Inter-agent message."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    recipient_id: str = ""  # Empty for broadcast
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class AgentCluster:
    """A cluster of related agents."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    agent_ids: Set[str] = field(default_factory=set)
    leader_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# AGENT BASE
# =============================================================================

class AgentBase(ABC):
    """Abstract base class for agents."""

    def __init__(
        self,
        agent_id: str = None,
        config: AgentConfig = None
    ):
        self.id = agent_id or str(uuid4())
        self.config = config or AgentConfig()
        self.state = AgentState.CREATED
        self.metrics = AgentMetrics()
        self.current_tasks: Dict[str, AgentTask] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    @property
    def capabilities(self) -> List[Capability]:
        """Get agent capabilities."""
        return self.config.capabilities

    @property
    def load(self) -> float:
        """Get current load (0.0 to 1.0)."""
        return len(self.current_tasks) / self.config.max_concurrent_tasks

    def has_capability(self, name: str, min_level: float = 0.0) -> bool:
        """Check if agent has a capability."""
        for cap in self.capabilities:
            if cap.name == name and cap.level >= min_level:
                return True
        return False

    async def initialize(self) -> None:
        """Initialize the agent."""
        self.state = AgentState.INITIALIZING
        await self._on_initialize()
        self.state = AgentState.IDLE

    async def _on_initialize(self) -> None:
        """Hook for subclass initialization."""
        pass

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> Any:
        """Execute a task."""
        pass

    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle an incoming message."""
        return None

    async def start(self) -> None:
        """Start the agent."""
        self._running = True
        await self.initialize()

        # Start message processing loop
        asyncio.create_task(self._message_loop())

    async def stop(self) -> None:
        """Stop the agent."""
        self.state = AgentState.STOPPING
        self._running = False

        # Wait for current tasks
        while self.current_tasks:
            await asyncio.sleep(0.1)

        self.state = AgentState.STOPPED

    async def _message_loop(self) -> None:
        """Process incoming messages."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self.handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Agent {self.id} message error: {e}")

    def assign_task(self, task: AgentTask) -> bool:
        """Assign a task to this agent."""
        if len(self.current_tasks) >= self.config.max_concurrent_tasks:
            return False

        task.assigned_agent = self.id
        task.started_at = datetime.now()
        self.current_tasks[task.id] = task
        self.state = AgentState.BUSY

        return True

    async def complete_task(
        self,
        task_id: str,
        result: Any = None,
        error: str = None
    ) -> None:
        """Mark a task as complete."""
        if task_id not in self.current_tasks:
            return

        task = self.current_tasks.pop(task_id)
        task.completed_at = datetime.now()
        task.result = result
        task.error = error

        duration = (task.completed_at - task.started_at).total_seconds()
        self.metrics.update_completion(error is None, duration)

        if not self.current_tasks:
            self.state = AgentState.IDLE

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "id": self.id,
            "type": self.config.type.value,
            "state": self.state.value,
            "load": self.load,
            "current_tasks": len(self.current_tasks),
            "metrics": {
                "completed": self.metrics.tasks_completed,
                "failed": self.metrics.tasks_failed,
                "success_rate": f"{self.metrics.success_rate:.2%}",
                "avg_response_time": f"{self.metrics.average_response_time:.2f}s"
            },
            "capabilities": [c.name for c in self.capabilities]
        }


# =============================================================================
# CONCRETE AGENTS
# =============================================================================

class WorkerAgent(AgentBase):
    """A general-purpose worker agent."""

    def __init__(
        self,
        agent_id: str = None,
        config: AgentConfig = None,
        task_handler: Callable = None
    ):
        super().__init__(agent_id, config)
        self.task_handler = task_handler

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute a task."""
        if self.task_handler:
            if asyncio.iscoroutinefunction(self.task_handler):
                return await self.task_handler(task)
            return self.task_handler(task)

        # Default: return payload
        return {"processed": True, "task_id": task.id}


class SpecialistAgent(AgentBase):
    """A domain-specialist agent."""

    def __init__(
        self,
        agent_id: str = None,
        config: AgentConfig = None,
        domain: str = ""
    ):
        config = config or AgentConfig(type=AgentType.SPECIALIST)
        super().__init__(agent_id, config)
        self.domain = domain
        self.knowledge_base: Dict[str, Any] = {}

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute a specialized task."""
        # Check if task matches domain
        task_domain = task.payload.get("domain", "")

        if task_domain and task_domain != self.domain:
            return {
                "error": f"Domain mismatch: expected {self.domain}, got {task_domain}"
            }

        # Process based on domain
        return {
            "domain": self.domain,
            "processed": True,
            "task_id": task.id,
            "specialist": self.id
        }


class SupervisorAgent(AgentBase):
    """An agent that supervises other agents."""

    def __init__(
        self,
        agent_id: str = None,
        config: AgentConfig = None
    ):
        config = config or AgentConfig(type=AgentType.SUPERVISOR)
        super().__init__(agent_id, config)
        self.supervised_agents: Set[str] = set()
        self.agent_statuses: Dict[str, Dict] = {}

    def add_supervised(self, agent_id: str) -> None:
        """Add an agent to supervise."""
        self.supervised_agents.add(agent_id)

    def remove_supervised(self, agent_id: str) -> None:
        """Remove an agent from supervision."""
        self.supervised_agents.discard(agent_id)

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute supervision task."""
        return {
            "supervised_count": len(self.supervised_agents),
            "task_id": task.id
        }

    async def check_agent(self, agent: AgentBase) -> Dict[str, Any]:
        """Check an agent's health."""
        status = agent.get_status()
        self.agent_statuses[agent.id] = status
        return status


# =============================================================================
# AGENT POOL
# =============================================================================

class AgentPool:
    """Manages a pool of agents."""

    def __init__(
        self,
        min_agents: int = 1,
        max_agents: int = 10,
        agent_factory: Callable[[], AgentBase] = None
    ):
        self.min_agents = min_agents
        self.max_agents = max_agents
        self.agent_factory = agent_factory or self._default_factory
        self.agents: Dict[str, AgentBase] = {}
        self.available: Set[str] = set()
        self.busy: Set[str] = set()

    def _default_factory(self) -> AgentBase:
        """Default agent factory."""
        return WorkerAgent()

    async def initialize(self) -> None:
        """Initialize the pool with minimum agents."""
        for _ in range(self.min_agents):
            await self.spawn_agent()

    async def spawn_agent(self) -> Optional[AgentBase]:
        """Spawn a new agent."""
        if len(self.agents) >= self.max_agents:
            return None

        agent = self.agent_factory()
        await agent.start()

        self.agents[agent.id] = agent
        self.available.add(agent.id)

        return agent

    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent."""
        if agent_id not in self.agents:
            return False

        if len(self.agents) <= self.min_agents:
            return False

        agent = self.agents[agent_id]
        await agent.stop()

        del self.agents[agent_id]
        self.available.discard(agent_id)
        self.busy.discard(agent_id)

        return True

    def get_available(self) -> List[AgentBase]:
        """Get available agents."""
        return [
            self.agents[aid] for aid in self.available
            if aid in self.agents
        ]

    def acquire(self, agent_id: str = None) -> Optional[AgentBase]:
        """Acquire an agent from the pool."""
        if agent_id:
            if agent_id in self.available:
                self.available.discard(agent_id)
                self.busy.add(agent_id)
                return self.agents.get(agent_id)
            return None

        if not self.available:
            return None

        agent_id = next(iter(self.available))
        self.available.discard(agent_id)
        self.busy.add(agent_id)

        return self.agents.get(agent_id)

    def release(self, agent_id: str) -> None:
        """Release an agent back to the pool."""
        if agent_id in self.busy:
            self.busy.discard(agent_id)
            self.available.add(agent_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "total_agents": len(self.agents),
            "available": len(self.available),
            "busy": len(self.busy),
            "min_agents": self.min_agents,
            "max_agents": self.max_agents,
            "utilization": len(self.busy) / len(self.agents) if self.agents else 0.0
        }


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Distributes work across agents."""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.round_robin_index = 0
        self.weights: Dict[str, float] = {}

    def select_agent(
        self,
        agents: List[AgentBase],
        task: AgentTask = None
    ) -> Optional[AgentBase]:
        """Select an agent for a task."""
        if not agents:
            return None

        # Filter by capability if task has requirements
        if task and task.required_capabilities:
            agents = [
                a for a in agents
                if all(a.has_capability(cap) for cap in task.required_capabilities)
            ]

        if not agents:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(agents)
        elif self.strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._least_loaded(agents)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random(agents)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted(agents)
        elif self.strategy == LoadBalancingStrategy.CAPABILITY_BASED:
            return self._capability_based(agents, task)

        return agents[0]

    def _round_robin(self, agents: List[AgentBase]) -> AgentBase:
        """Round-robin selection."""
        agent = agents[self.round_robin_index % len(agents)]
        self.round_robin_index += 1
        return agent

    def _least_loaded(self, agents: List[AgentBase]) -> AgentBase:
        """Select least loaded agent."""
        return min(agents, key=lambda a: a.load)

    def _random(self, agents: List[AgentBase]) -> AgentBase:
        """Random selection."""
        return random.choice(agents)

    def _weighted(self, agents: List[AgentBase]) -> AgentBase:
        """Weighted random selection."""
        weighted = []
        for agent in agents:
            weight = self.weights.get(agent.id, 1.0)
            weighted.append((agent, weight))

        total = sum(w for _, w in weighted)
        r = random.uniform(0, total)

        cumulative = 0
        for agent, weight in weighted:
            cumulative += weight
            if r <= cumulative:
                return agent

        return agents[0]

    def _capability_based(
        self,
        agents: List[AgentBase],
        task: AgentTask
    ) -> AgentBase:
        """Select based on capability match."""
        if not task or not task.required_capabilities:
            return self._least_loaded(agents)

        # Score agents by capability match
        scored = []
        for agent in agents:
            score = 0
            for cap_name in task.required_capabilities:
                for cap in agent.capabilities:
                    if cap.name == cap_name:
                        score += cap.level
            scored.append((agent, score))

        # Select highest scored (prefer less loaded if tied)
        scored.sort(key=lambda x: (-x[1], x[0].load))
        return scored[0][0]

    def set_weight(self, agent_id: str, weight: float) -> None:
        """Set agent weight for weighted strategy."""
        self.weights[agent_id] = max(0.1, weight)


# =============================================================================
# MESSAGE BROKER
# =============================================================================

class MessageBroker:
    """Handles inter-agent communication."""

    def __init__(self):
        self.agents: Dict[str, AgentBase] = {}
        self.topics: Dict[str, Set[str]] = defaultdict(set)
        self.message_handlers: Dict[str, Callable] = {}
        self.message_history: List[Message] = []
        self.max_history = 1000

    def register_agent(self, agent: AgentBase) -> None:
        """Register an agent."""
        self.agents[agent.id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]

        # Remove from all topics
        for topic in self.topics.values():
            topic.discard(agent_id)

    def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe agent to a topic."""
        self.topics[topic].add(agent_id)

    def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe agent from a topic."""
        if topic in self.topics:
            self.topics[topic].discard(agent_id)

    async def send(self, message: Message) -> bool:
        """Send a message to a specific agent."""
        recipient = self.agents.get(message.recipient_id)

        if not recipient:
            return False

        await recipient.message_queue.put(message)
        self._record_message(message)

        return True

    async def broadcast(
        self,
        message: Message,
        topic: str = None
    ) -> int:
        """Broadcast a message."""
        message.type = MessageType.BROADCAST
        sent_count = 0

        if topic:
            # Send to topic subscribers
            subscribers = self.topics.get(topic, set())
            targets = [
                self.agents[aid] for aid in subscribers
                if aid in self.agents and aid != message.sender_id
            ]
        else:
            # Send to all agents
            targets = [
                a for a in self.agents.values()
                if a.id != message.sender_id
            ]

        for agent in targets:
            await agent.message_queue.put(message)
            sent_count += 1

        self._record_message(message)
        return sent_count

    async def request_response(
        self,
        message: Message,
        timeout: float = 30.0
    ) -> Optional[Message]:
        """Send a request and wait for response."""
        message.type = MessageType.REQUEST
        response_queue = asyncio.Queue()

        # Register response handler
        correlation_id = message.id

        async def response_handler(response: Message):
            if response.correlation_id == correlation_id:
                await response_queue.put(response)

        self.message_handlers[correlation_id] = response_handler

        try:
            await self.send(message)
            response = await asyncio.wait_for(
                response_queue.get(),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            return None
        finally:
            if correlation_id in self.message_handlers:
                del self.message_handlers[correlation_id]

    def _record_message(self, message: Message) -> None:
        """Record message in history."""
        self.message_history.append(message)

        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            "registered_agents": len(self.agents),
            "topics": len(self.topics),
            "total_subscribers": sum(len(s) for s in self.topics.values()),
            "message_history": len(self.message_history)
        }


# =============================================================================
# AUTO SCALER
# =============================================================================

class AutoScaler:
    """Automatically scales agent pool based on load."""

    def __init__(
        self,
        pool: AgentPool,
        mode: ScalingMode = ScalingMode.AUTO
    ):
        self.pool = pool
        self.mode = mode
        self.scale_up_threshold = 0.8
        self.scale_down_threshold = 0.3
        self.cooldown_seconds = 60
        self.last_scale_action: Optional[datetime] = None
        self.load_history: List[Tuple[datetime, float]] = []

    async def check_and_scale(self) -> Dict[str, Any]:
        """Check load and scale if necessary."""
        if self.mode == ScalingMode.MANUAL:
            return {"action": "none", "reason": "manual mode"}

        # Check cooldown
        if self.last_scale_action:
            elapsed = (datetime.now() - self.last_scale_action).total_seconds()
            if elapsed < self.cooldown_seconds:
                return {"action": "none", "reason": "cooldown"}

        # Calculate current load
        stats = self.pool.get_stats()
        current_load = stats["utilization"]

        # Record load history
        self.load_history.append((datetime.now(), current_load))
        self._trim_history()

        if self.mode == ScalingMode.PREDICTIVE:
            return await self._predictive_scale(current_load)

        return await self._reactive_scale(current_load)

    async def _reactive_scale(self, current_load: float) -> Dict[str, Any]:
        """Reactive scaling based on current load."""
        if current_load >= self.scale_up_threshold:
            # Scale up
            agent = await self.pool.spawn_agent()
            if agent:
                self.last_scale_action = datetime.now()
                return {
                    "action": "scale_up",
                    "reason": f"load {current_load:.2%} >= threshold {self.scale_up_threshold:.2%}",
                    "new_agent": agent.id
                }
        elif current_load <= self.scale_down_threshold:
            # Scale down
            if len(self.pool.available) > 0:
                agent_id = next(iter(self.pool.available))
                if await self.pool.terminate_agent(agent_id):
                    self.last_scale_action = datetime.now()
                    return {
                        "action": "scale_down",
                        "reason": f"load {current_load:.2%} <= threshold {self.scale_down_threshold:.2%}",
                        "removed_agent": agent_id
                    }

        return {"action": "none", "reason": "load within thresholds"}

    async def _predictive_scale(self, current_load: float) -> Dict[str, Any]:
        """Predictive scaling based on load trend."""
        if len(self.load_history) < 5:
            return await self._reactive_scale(current_load)

        # Calculate trend
        recent = self.load_history[-5:]
        loads = [l for _, l in recent]
        trend = (loads[-1] - loads[0]) / len(loads)

        # Predict future load
        predicted_load = current_load + (trend * 3)  # 3 intervals ahead

        if predicted_load >= self.scale_up_threshold:
            agent = await self.pool.spawn_agent()
            if agent:
                self.last_scale_action = datetime.now()
                return {
                    "action": "predictive_scale_up",
                    "reason": f"predicted load {predicted_load:.2%}",
                    "trend": trend,
                    "new_agent": agent.id
                }

        return await self._reactive_scale(current_load)

    def _trim_history(self) -> None:
        """Keep only recent history."""
        max_history = 100
        if len(self.load_history) > max_history:
            self.load_history = self.load_history[-max_history:]

    def configure(
        self,
        scale_up_threshold: float = None,
        scale_down_threshold: float = None,
        cooldown_seconds: int = None
    ) -> None:
        """Configure scaling parameters."""
        if scale_up_threshold is not None:
            self.scale_up_threshold = scale_up_threshold
        if scale_down_threshold is not None:
            self.scale_down_threshold = scale_down_threshold
        if cooldown_seconds is not None:
            self.cooldown_seconds = cooldown_seconds


# =============================================================================
# AGENT COORDINATOR
# =============================================================================

class AgentCoordinator:
    """
    The master agent coordinator for BAEL.

    Manages agent lifecycle, work distribution,
    communication, and scaling.
    """

    def __init__(self):
        self.pools: Dict[str, AgentPool] = {}
        self.agents: Dict[str, AgentBase] = {}
        self.clusters: Dict[str, AgentCluster] = {}
        self.load_balancer = LoadBalancer()
        self.message_broker = MessageBroker()
        self.auto_scalers: Dict[str, AutoScaler] = {}

        # Task management
        self.task_queue: List[AgentTask] = []  # Priority heap
        self.pending_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}

        # Coordination state
        self._running = False
        self._task_processor: Optional[asyncio.Task] = None

    async def create_pool(
        self,
        name: str,
        min_agents: int = 1,
        max_agents: int = 10,
        agent_factory: Callable[[], AgentBase] = None,
        auto_scale: bool = True
    ) -> AgentPool:
        """Create an agent pool."""
        pool = AgentPool(
            min_agents=min_agents,
            max_agents=max_agents,
            agent_factory=agent_factory
        )

        await pool.initialize()

        self.pools[name] = pool

        # Register agents
        for agent in pool.agents.values():
            self.agents[agent.id] = agent
            self.message_broker.register_agent(agent)

        # Set up auto-scaler
        if auto_scale:
            self.auto_scalers[name] = AutoScaler(pool, ScalingMode.AUTO)

        return pool

    async def spawn_agent(
        self,
        agent_class: Type[AgentBase],
        config: AgentConfig = None,
        pool_name: str = None
    ) -> AgentBase:
        """Spawn a standalone agent."""
        agent = agent_class(config=config)
        await agent.start()

        self.agents[agent.id] = agent
        self.message_broker.register_agent(agent)

        return agent

    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate an agent."""
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]
        await agent.stop()

        del self.agents[agent_id]
        self.message_broker.unregister_agent(agent_id)

        return True

    async def submit_task(
        self,
        task: AgentTask,
        pool_name: str = None
    ) -> str:
        """Submit a task for execution."""
        self.pending_tasks[task.id] = task
        heapq.heappush(self.task_queue, task)

        return task.id

    async def _process_tasks(self) -> None:
        """Process task queue."""
        while self._running:
            if not self.task_queue:
                await asyncio.sleep(0.1)
                continue

            # Get highest priority task
            task = heapq.heappop(self.task_queue)

            # Find available agents
            available = [
                a for a in self.agents.values()
                if a.state == AgentState.IDLE
            ]

            if not available:
                # Re-queue task
                heapq.heappush(self.task_queue, task)
                await asyncio.sleep(0.1)
                continue

            # Select agent
            agent = self.load_balancer.select_agent(available, task)

            if not agent:
                heapq.heappush(self.task_queue, task)
                await asyncio.sleep(0.1)
                continue

            # Assign and execute
            if agent.assign_task(task):
                asyncio.create_task(self._execute_task(agent, task))

    async def _execute_task(
        self,
        agent: AgentBase,
        task: AgentTask
    ) -> None:
        """Execute a task on an agent."""
        try:
            result = await asyncio.wait_for(
                agent.execute_task(task),
                timeout=task.timeout_seconds
            )
            await agent.complete_task(task.id, result=result)
            task.result = result
        except asyncio.TimeoutError:
            await agent.complete_task(task.id, error="Task timeout")
            task.error = "Task timeout"
        except Exception as e:
            await agent.complete_task(task.id, error=str(e))
            task.error = str(e)
        finally:
            if task.id in self.pending_tasks:
                del self.pending_tasks[task.id]
            self.completed_tasks[task.id] = task

    async def get_task_result(
        self,
        task_id: str,
        timeout: float = 300.0
    ) -> Optional[Any]:
        """Wait for and get task result."""
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                if task.error:
                    raise Exception(task.error)
                return task.result

            await asyncio.sleep(0.1)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

    def create_cluster(
        self,
        name: str,
        agent_ids: List[str] = None
    ) -> AgentCluster:
        """Create an agent cluster."""
        cluster = AgentCluster(name=name)

        if agent_ids:
            for aid in agent_ids:
                if aid in self.agents:
                    cluster.agent_ids.add(aid)

        self.clusters[cluster.id] = cluster
        return cluster

    async def broadcast_to_cluster(
        self,
        cluster_id: str,
        message: Message
    ) -> int:
        """Broadcast to all agents in a cluster."""
        if cluster_id not in self.clusters:
            return 0

        cluster = self.clusters[cluster_id]
        sent = 0

        for agent_id in cluster.agent_ids:
            msg_copy = Message(
                type=message.type,
                sender_id=message.sender_id,
                recipient_id=agent_id,
                content=message.content.copy()
            )
            if await self.message_broker.send(msg_copy):
                sent += 1

        return sent

    async def start(self) -> None:
        """Start the coordinator."""
        self._running = True
        self._task_processor = asyncio.create_task(self._process_tasks())

        # Start auto-scaling
        asyncio.create_task(self._auto_scale_loop())

    async def stop(self) -> None:
        """Stop the coordinator."""
        self._running = False

        if self._task_processor:
            self._task_processor.cancel()

        # Stop all agents
        for agent in list(self.agents.values()):
            await agent.stop()

    async def _auto_scale_loop(self) -> None:
        """Periodic auto-scaling check."""
        while self._running:
            for scaler in self.auto_scalers.values():
                await scaler.check_and_scale()
            await asyncio.sleep(10)

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        agent_states = defaultdict(int)
        for agent in self.agents.values():
            agent_states[agent.state.value] += 1

        return {
            "total_agents": len(self.agents),
            "pools": len(self.pools),
            "clusters": len(self.clusters),
            "agent_states": dict(agent_states),
            "pending_tasks": len(self.pending_tasks),
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "message_broker": self.message_broker.get_stats()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Agent Coordinator."""
    print("=" * 70)
    print("BAEL - AGENT COORDINATOR DEMO")
    print("Comprehensive Agent Lifecycle Management")
    print("=" * 70)
    print()

    # Create coordinator
    coordinator = AgentCoordinator()
    await coordinator.start()

    # 1. Create Agent Pool
    print("1. CREATING AGENT POOL:")
    print("-" * 40)

    def worker_factory():
        config = AgentConfig(
            type=AgentType.WORKER,
            capabilities=[
                Capability("text_processing", 0.9),
                Capability("data_analysis", 0.7)
            ],
            max_concurrent_tasks=3
        )
        return WorkerAgent(config=config)

    pool = await coordinator.create_pool(
        "worker_pool",
        min_agents=2,
        max_agents=5,
        agent_factory=worker_factory
    )

    print(f"   Created pool with {len(pool.agents)} agents")
    for agent_id, agent in pool.agents.items():
        print(f"   - {agent_id[:8]}... ({agent.config.type.value})")
    print()

    # 2. Spawn Specialist Agent
    print("2. SPAWNING SPECIALIST AGENT:")
    print("-" * 40)

    specialist_config = AgentConfig(
        type=AgentType.SPECIALIST,
        capabilities=[Capability("nlp", 0.95)],
        max_concurrent_tasks=2
    )

    specialist = await coordinator.spawn_agent(
        SpecialistAgent,
        config=specialist_config
    )
    specialist.domain = "nlp"

    print(f"   Specialist spawned: {specialist.id[:8]}...")
    print(f"   Domain: {specialist.domain}")
    print()

    # 3. Submit Tasks
    print("3. SUBMITTING TASKS:")
    print("-" * 40)

    tasks = []
    for i in range(5):
        task = AgentTask(
            name=f"Task-{i+1}",
            payload={"data": f"process item {i+1}"},
            priority=TaskPriority.NORMAL if i < 3 else TaskPriority.HIGH
        )
        task_id = await coordinator.submit_task(task)
        tasks.append(task_id)
        print(f"   Submitted: {task.name} (Priority: {task.priority.name})")
    print()

    # Wait for tasks to process
    await asyncio.sleep(1)

    # 4. Task Status
    print("4. TASK STATUS:")
    print("-" * 40)

    print(f"   Pending: {len(coordinator.pending_tasks)}")
    print(f"   Queued: {len(coordinator.task_queue)}")
    print(f"   Completed: {len(coordinator.completed_tasks)}")
    print()

    # 5. Inter-Agent Communication
    print("5. INTER-AGENT COMMUNICATION:")
    print("-" * 40)

    # Get two agents
    agents = list(coordinator.agents.values())[:2]
    if len(agents) >= 2:
        sender, receiver = agents[0], agents[1]

        message = Message(
            type=MessageType.REQUEST,
            sender_id=sender.id,
            recipient_id=receiver.id,
            content={"action": "ping", "data": "hello"}
        )

        sent = await coordinator.message_broker.send(message)
        print(f"   Message sent: {sent}")
        print(f"   From: {sender.id[:8]}... To: {receiver.id[:8]}...")

    # Subscribe to topic
    coordinator.message_broker.subscribe(agents[0].id, "updates")
    print(f"   Agent subscribed to 'updates' topic")
    print()

    # 6. Load Balancing
    print("6. LOAD BALANCING:")
    print("-" * 40)

    available = [a for a in coordinator.agents.values() if a.state == AgentState.IDLE]

    strategies = [
        LoadBalancingStrategy.ROUND_ROBIN,
        LoadBalancingStrategy.LEAST_LOADED,
        LoadBalancingStrategy.RANDOM
    ]

    for strategy in strategies:
        coordinator.load_balancer.strategy = strategy
        selected = coordinator.load_balancer.select_agent(available)
        if selected:
            print(f"   {strategy.value}: Selected {selected.id[:8]}...")
    print()

    # 7. Agent Clusters
    print("7. AGENT CLUSTERS:")
    print("-" * 40)

    cluster = coordinator.create_cluster(
        "worker_cluster",
        agent_ids=list(pool.agents.keys())
    )
    print(f"   Created cluster: {cluster.name}")
    print(f"   Agents in cluster: {len(cluster.agent_ids)}")

    # Broadcast to cluster
    broadcast_msg = Message(
        type=MessageType.BROADCAST,
        sender_id="coordinator",
        content={"notification": "cluster update"}
    )
    sent_count = await coordinator.broadcast_to_cluster(cluster.id, broadcast_msg)
    print(f"   Broadcast sent to {sent_count} agents")
    print()

    # 8. Agent Status
    print("8. AGENT STATUS:")
    print("-" * 40)

    for agent_id, agent in list(coordinator.agents.items())[:3]:
        status = agent.get_status()
        print(f"   {agent_id[:8]}...")
        print(f"     State: {status['state']}")
        print(f"     Load: {status['load']:.2%}")
        print(f"     Tasks: {status['current_tasks']}")
    print()

    # 9. Auto-Scaling
    print("9. AUTO-SCALING:")
    print("-" * 40)

    scaler = coordinator.auto_scalers.get("worker_pool")
    if scaler:
        scaler.configure(
            scale_up_threshold=0.7,
            scale_down_threshold=0.2
        )
        print(f"   Scale up threshold: {scaler.scale_up_threshold:.0%}")
        print(f"   Scale down threshold: {scaler.scale_down_threshold:.0%}")

        result = await scaler.check_and_scale()
        print(f"   Scaling action: {result['action']}")
    print()

    # 10. Statistics
    print("10. COORDINATOR STATISTICS:")
    print("-" * 40)

    stats = coordinator.get_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     {k}: {v}")
        else:
            print(f"   {key}: {value}")
    print()

    # Cleanup
    await coordinator.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Agent Coordinator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
