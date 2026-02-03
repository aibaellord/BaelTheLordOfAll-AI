"""
BAEL - Agent Swarm Orchestration
Coordinate large swarms of specialized agents for complex tasks.

Features:
- Swarm coordination
- Task distribution
- Agent discovery
- Load balancing
- Fault tolerance
- Emergent behavior
"""

import asyncio
import hashlib
import heapq
import json
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """States of a swarm agent."""
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"
    INITIALIZING = "initializing"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class DistributionStrategy(Enum):
    """Task distribution strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    CAPABILITY_MATCH = "capability_match"
    AFFINITY = "affinity"
    WEIGHTED = "weighted"


class CoordinationMode(Enum):
    """Swarm coordination modes."""
    CENTRALIZED = "centralized"
    DECENTRALIZED = "decentralized"
    HIERARCHICAL = "hierarchical"
    MESH = "mesh"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SwarmAgent:
    """An agent in the swarm."""
    id: str
    name: str
    capabilities: Set[str] = field(default_factory=set)
    state: AgentState = AgentState.INITIALIZING
    current_task: Optional[str] = None
    completed_tasks: int = 0
    failed_tasks: int = 0
    load: float = 0.0  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=datetime.now)

    @property
    def is_available(self) -> bool:
        return self.state == AgentState.IDLE

    @property
    def success_rate(self) -> float:
        total = self.completed_tasks + self.failed_tasks
        return self.completed_tasks / total if total > 0 else 1.0


@dataclass
class SwarmTask:
    """A task for the swarm."""
    id: str
    name: str
    description: str
    required_capabilities: Set[str] = field(default_factory=set)
    priority: TaskPriority = TaskPriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: float = 300
    retries: int = 0
    max_retries: int = 3

    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority.value < other.priority.value


@dataclass
class SwarmMessage:
    """Message in the swarm."""
    id: str
    sender: str
    recipient: Optional[str]  # None = broadcast
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SwarmMetrics:
    """Swarm performance metrics."""
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    throughput: float = 0.0  # tasks per second


# =============================================================================
# TASK QUEUE
# =============================================================================

class TaskQueue:
    """Priority queue for tasks."""

    def __init__(self):
        self._queue: List[SwarmTask] = []
        self._task_map: Dict[str, SwarmTask] = {}
        self._lock = asyncio.Lock()

    async def push(self, task: SwarmTask) -> None:
        """Add a task to the queue."""
        async with self._lock:
            heapq.heappush(self._queue, task)
            self._task_map[task.id] = task

    async def pop(self) -> Optional[SwarmTask]:
        """Get the highest priority task."""
        async with self._lock:
            while self._queue:
                task = heapq.heappop(self._queue)
                if task.id in self._task_map and task.status == "pending":
                    return task
            return None

    async def get(self, task_id: str) -> Optional[SwarmTask]:
        """Get a task by ID."""
        async with self._lock:
            return self._task_map.get(task_id)

    async def remove(self, task_id: str) -> bool:
        """Remove a task."""
        async with self._lock:
            if task_id in self._task_map:
                del self._task_map[task_id]
                return True
            return False

    @property
    def size(self) -> int:
        return len([t for t in self._task_map.values() if t.status == "pending"])


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Distributes tasks across agents."""

    def __init__(self, strategy: DistributionStrategy = DistributionStrategy.LEAST_LOADED):
        self.strategy = strategy
        self._round_robin_index = 0
        self._agent_weights: Dict[str, float] = {}

    def select_agent(
        self,
        task: SwarmTask,
        agents: List[SwarmAgent]
    ) -> Optional[SwarmAgent]:
        """Select an agent for a task."""
        # Filter by capability
        capable_agents = [
            a for a in agents
            if a.is_available and task.required_capabilities.issubset(a.capabilities)
        ]

        if not capable_agents:
            return None

        if self.strategy == DistributionStrategy.ROUND_ROBIN:
            return self._round_robin(capable_agents)
        elif self.strategy == DistributionStrategy.LEAST_LOADED:
            return self._least_loaded(capable_agents)
        elif self.strategy == DistributionStrategy.RANDOM:
            return self._random(capable_agents)
        elif self.strategy == DistributionStrategy.CAPABILITY_MATCH:
            return self._capability_match(task, capable_agents)
        elif self.strategy == DistributionStrategy.WEIGHTED:
            return self._weighted(capable_agents)
        else:
            return capable_agents[0]

    def _round_robin(self, agents: List[SwarmAgent]) -> SwarmAgent:
        """Round-robin selection."""
        agent = agents[self._round_robin_index % len(agents)]
        self._round_robin_index += 1
        return agent

    def _least_loaded(self, agents: List[SwarmAgent]) -> SwarmAgent:
        """Select least loaded agent."""
        return min(agents, key=lambda a: a.load)

    def _random(self, agents: List[SwarmAgent]) -> SwarmAgent:
        """Random selection."""
        return random.choice(agents)

    def _capability_match(
        self,
        task: SwarmTask,
        agents: List[SwarmAgent]
    ) -> SwarmAgent:
        """Select agent with best capability match."""
        def match_score(agent: SwarmAgent) -> int:
            return len(agent.capabilities & task.required_capabilities)
        return max(agents, key=match_score)

    def _weighted(self, agents: List[SwarmAgent]) -> SwarmAgent:
        """Weighted random selection based on success rate."""
        weights = [a.success_rate * (1 - a.load) for a in agents]
        total = sum(weights)
        if total == 0:
            return random.choice(agents)

        r = random.random() * total
        cumulative = 0
        for agent, weight in zip(agents, weights):
            cumulative += weight
            if r <= cumulative:
                return agent
        return agents[-1]


# =============================================================================
# MESSAGE BUS
# =============================================================================

class SwarmMessageBus:
    """Message bus for swarm communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._agent_handlers: Dict[str, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def subscribe(self, message_type: str, handler: Callable) -> None:
        """Subscribe to a message type."""
        self._subscribers[message_type].append(handler)

    def register_agent(self, agent_id: str, handler: Callable) -> None:
        """Register an agent's message handler."""
        self._agent_handlers[agent_id] = handler

    async def publish(self, message: SwarmMessage) -> None:
        """Publish a message."""
        await self._message_queue.put(message)

    async def start(self) -> None:
        """Start message processing."""
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                await self._deliver(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message bus error: {e}")

    async def stop(self) -> None:
        """Stop message processing."""
        self._running = False

    async def _deliver(self, message: SwarmMessage) -> None:
        """Deliver a message."""
        # Type-based subscribers
        for handler in self._subscribers.get(message.type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Agent-specific delivery
        if message.recipient:
            handler = self._agent_handlers.get(message.recipient)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Agent handler error: {e}")
        else:
            # Broadcast to all agents
            for handler in self._agent_handlers.values():
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Broadcast handler error: {e}")


# =============================================================================
# SWARM CONTROLLER
# =============================================================================

class SwarmController:
    """Central swarm coordination."""

    def __init__(
        self,
        mode: CoordinationMode = CoordinationMode.CENTRALIZED,
        distribution_strategy: DistributionStrategy = DistributionStrategy.LEAST_LOADED
    ):
        self.mode = mode
        self.agents: Dict[str, SwarmAgent] = {}
        self.task_queue = TaskQueue()
        self.load_balancer = LoadBalancer(distribution_strategy)
        self.message_bus = SwarmMessageBus()

        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._completed_tasks: List[SwarmTask] = []
        self._failed_tasks: List[SwarmTask] = []

    async def start(self) -> None:
        """Start the swarm controller."""
        self._running = True

        # Start message bus
        asyncio.create_task(self.message_bus.start())

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Start monitor
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("Swarm controller started")

    async def stop(self) -> None:
        """Stop the swarm controller."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()

        await self.message_bus.stop()

        logger.info("Swarm controller stopped")

    def register_agent(self, agent: SwarmAgent) -> None:
        """Register an agent with the swarm."""
        self.agents[agent.id] = agent
        agent.state = AgentState.IDLE
        logger.info(f"Registered agent: {agent.id} ({agent.name})")

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the swarm."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    async def submit_task(self, task: SwarmTask) -> str:
        """Submit a task to the swarm."""
        await self.task_queue.push(task)
        logger.info(f"Task submitted: {task.id} ({task.name})")
        return task.id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        task = await self.task_queue.get(task_id)
        if task:
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "assigned_agent": task.assigned_agent,
                "result": task.result,
                "error": task.error
            }

        # Check completed/failed
        for t in self._completed_tasks + self._failed_tasks:
            if t.id == task_id:
                return {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status,
                    "assigned_agent": t.assigned_agent,
                    "result": t.result,
                    "error": t.error
                }

        return None

    async def _scheduler_loop(self) -> None:
        """Main scheduling loop."""
        while self._running:
            try:
                # Get available agents
                available_agents = [
                    a for a in self.agents.values()
                    if a.is_available
                ]

                if available_agents:
                    # Get next task
                    task = await self.task_queue.pop()

                    if task:
                        # Select agent
                        agent = self.load_balancer.select_agent(
                            task,
                            available_agents
                        )

                        if agent:
                            await self._assign_task(task, agent)
                        else:
                            # No capable agent, requeue
                            await self.task_queue.push(task)

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(1)

    async def _assign_task(self, task: SwarmTask, agent: SwarmAgent) -> None:
        """Assign a task to an agent."""
        task.assigned_agent = agent.id
        task.status = "assigned"
        task.started_at = datetime.now()

        agent.state = AgentState.BUSY
        agent.current_task = task.id
        agent.load = min(1.0, agent.load + 0.2)

        # Send assignment message
        message = SwarmMessage(
            id=hashlib.md5(f"assign_{task.id}".encode()).hexdigest()[:12],
            sender="controller",
            recipient=agent.id,
            type="task_assignment",
            payload={"task": task.__dict__}
        )

        await self.message_bus.publish(message)
        logger.info(f"Assigned task {task.id} to agent {agent.id}")

    async def report_completion(
        self,
        task_id: str,
        result: Any,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Report task completion."""
        task = await self.task_queue.get(task_id)
        if not task:
            return

        agent = self.agents.get(task.assigned_agent)

        if success:
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now()
            self._completed_tasks.append(task)

            if agent:
                agent.completed_tasks += 1
        else:
            if task.retries < task.max_retries:
                # Retry
                task.retries += 1
                task.status = "pending"
                task.assigned_agent = None
                await self.task_queue.push(task)
            else:
                task.status = "failed"
                task.error = error
                self._failed_tasks.append(task)

                if agent:
                    agent.failed_tasks += 1

        # Free up agent
        if agent:
            agent.state = AgentState.IDLE
            agent.current_task = None
            agent.load = max(0, agent.load - 0.2)

        await self.task_queue.remove(task_id)

    async def _monitor_loop(self) -> None:
        """Monitor agent health."""
        while self._running:
            try:
                now = datetime.now()
                timeout = timedelta(seconds=30)

                for agent in list(self.agents.values()):
                    if now - agent.last_heartbeat > timeout:
                        agent.state = AgentState.OFFLINE
                        logger.warning(f"Agent {agent.id} is offline")

                        # Reassign task if any
                        if agent.current_task:
                            task = await self.task_queue.get(agent.current_task)
                            if task:
                                task.status = "pending"
                                task.assigned_agent = None
                                await self.task_queue.push(task)

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(1)

    def heartbeat(self, agent_id: str) -> None:
        """Process agent heartbeat."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.last_heartbeat = datetime.now()
            if agent.state == AgentState.OFFLINE:
                agent.state = AgentState.IDLE

    def get_metrics(self) -> SwarmMetrics:
        """Get swarm metrics."""
        agents = list(self.agents.values())

        metrics = SwarmMetrics(
            total_agents=len(agents),
            active_agents=sum(1 for a in agents if a.state == AgentState.BUSY),
            idle_agents=sum(1 for a in agents if a.state == AgentState.IDLE),
            pending_tasks=self.task_queue.size,
            running_tasks=sum(1 for a in agents if a.current_task),
            completed_tasks=len(self._completed_tasks),
            failed_tasks=len(self._failed_tasks)
        )

        # Calculate average task duration
        completed_with_times = [
            t for t in self._completed_tasks
            if t.started_at and t.completed_at
        ]

        if completed_with_times:
            durations = [
                (t.completed_at - t.started_at).total_seconds()
                for t in completed_with_times
            ]
            metrics.avg_task_duration = sum(durations) / len(durations)

        return metrics


# =============================================================================
# SWARM BUILDER
# =============================================================================

class SwarmBuilder:
    """Builder for creating agent swarms."""

    def __init__(self, name: str):
        self.name = name
        self._agents: List[SwarmAgent] = []
        self._controller: Optional[SwarmController] = None

    def with_mode(self, mode: CoordinationMode) -> "SwarmBuilder":
        """Set coordination mode."""
        self._controller = SwarmController(mode=mode)
        return self

    def with_strategy(self, strategy: DistributionStrategy) -> "SwarmBuilder":
        """Set distribution strategy."""
        if self._controller:
            self._controller.load_balancer.strategy = strategy
        return self

    def add_agent(
        self,
        name: str,
        capabilities: Optional[Set[str]] = None
    ) -> "SwarmBuilder":
        """Add an agent."""
        agent_id = hashlib.md5(f"{name}_{len(self._agents)}".encode()).hexdigest()[:12]
        agent = SwarmAgent(
            id=agent_id,
            name=name,
            capabilities=capabilities or set()
        )
        self._agents.append(agent)
        return self

    def add_agents(
        self,
        count: int,
        name_prefix: str,
        capabilities: Optional[Set[str]] = None
    ) -> "SwarmBuilder":
        """Add multiple agents."""
        for i in range(count):
            self.add_agent(f"{name_prefix}_{i+1}", capabilities)
        return self

    def build(self) -> SwarmController:
        """Build and return the swarm controller."""
        if not self._controller:
            self._controller = SwarmController()

        for agent in self._agents:
            self._controller.register_agent(agent)

        return self._controller


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_swarm():
    """Demonstrate swarm capabilities."""

    # Build swarm
    controller = (
        SwarmBuilder("bael_swarm")
        .with_mode(CoordinationMode.CENTRALIZED)
        .with_strategy(DistributionStrategy.LEAST_LOADED)
        .add_agents(3, "worker", {"code", "research"})
        .add_agents(2, "specialist", {"code", "review", "test"})
        .add_agent("coordinator", {"planning", "review"})
        .build()
    )

    # Start swarm
    await controller.start()

    # Submit tasks
    for i in range(5):
        task = SwarmTask(
            id=f"task_{i}",
            name=f"Task {i}",
            description=f"Task number {i}",
            required_capabilities={"code"} if i % 2 == 0 else {"research"},
            priority=TaskPriority.NORMAL
        )
        await controller.submit_task(task)

    # Wait and check metrics
    await asyncio.sleep(1)

    metrics = controller.get_metrics()
    print(f"Total agents: {metrics.total_agents}")
    print(f"Active: {metrics.active_agents}, Idle: {metrics.idle_agents}")
    print(f"Pending tasks: {metrics.pending_tasks}")

    # Stop swarm
    await controller.stop()


if __name__ == "__main__":
    asyncio.run(example_swarm())
