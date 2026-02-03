#!/usr/bin/env python3
"""
BAEL - Agent Orchestrator
Advanced agent orchestration and coordination.

Features:
- Multi-agent coordination
- Agent lifecycle management
- Task distribution
- Agent communication
- Load balancing
- Fault tolerance
- Agent pools
- Hierarchical agents
"""

import asyncio
import copy
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AgentStatus(Enum):
    """Agent status."""
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AgentRole(Enum):
    """Agent role."""
    WORKER = "worker"
    SUPERVISOR = "supervisor"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class TaskPriority(Enum):
    """Task priority."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    BACKGROUND = 1


class DistributionStrategy(Enum):
    """Task distribution strategy."""
    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    RANDOM = "random"
    CAPABILITY_BASED = "capability_based"
    AFFINITY = "affinity"


class MessageType(Enum):
    """Message type."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    COMMAND = "command"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AgentCapability:
    """Agent capability."""
    name: str
    level: float = 1.0  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Agent configuration."""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.WORKER
    capabilities: List[AgentCapability] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    timeout: float = 300.0
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    """Task for agent."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    payload: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AgentMessage:
    """Agent message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    sender: str = ""
    recipient: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None


@dataclass
class AgentStats:
    """Agent statistics."""
    agent_id: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_duration: float = 0.0
    current_tasks: int = 0
    uptime: float = 0.0


# =============================================================================
# AGENT BASE
# =============================================================================

class Agent(ABC):
    """Base agent."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.IDLE
        self.current_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self._started_at = datetime.now()
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> AgentRole:
        return self.config.role

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> Any:
        """Execute task."""
        pass

    async def accept_task(self, task: AgentTask) -> bool:
        """Accept task."""
        if len(self.current_tasks) >= self.config.max_concurrent_tasks:
            return False

        if not self._has_required_capabilities(task):
            return False

        task.assigned_agent = self.agent_id
        task.status = "assigned"
        self.current_tasks[task.task_id] = task
        return True

    async def run_task(self, task: AgentTask) -> Any:
        """Run task."""
        task.started_at = datetime.now()
        task.status = "running"
        self.status = AgentStatus.BUSY

        try:
            result = await asyncio.wait_for(
                self.execute_task(task),
                timeout=self.config.timeout
            )

            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()
            self.completed_tasks.append(task.task_id)

            return result

        except asyncio.TimeoutError:
            task.error = "Task timeout"
            task.status = "failed"
            self.failed_tasks.append(task.task_id)
            raise

        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            self.failed_tasks.append(task.task_id)
            raise

        finally:
            if task.task_id in self.current_tasks:
                del self.current_tasks[task.task_id]

            if not self.current_tasks:
                self.status = AgentStatus.IDLE

    def _has_required_capabilities(self, task: AgentTask) -> bool:
        """Check capabilities."""
        if not task.required_capabilities:
            return True

        agent_caps = {c.name for c in self.config.capabilities}
        return all(cap in agent_caps for cap in task.required_capabilities)

    async def send_message(self, message: AgentMessage) -> None:
        """Send message."""
        await self._message_queue.put(message)

    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive message."""
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def get_stats(self) -> AgentStats:
        """Get statistics."""
        completed_count = len(self.completed_tasks)
        failed_count = len(self.failed_tasks)
        uptime = (datetime.now() - self._started_at).total_seconds()

        return AgentStats(
            agent_id=self.agent_id,
            tasks_completed=completed_count,
            tasks_failed=failed_count,
            current_tasks=len(self.current_tasks),
            uptime=uptime
        )


# =============================================================================
# WORKER AGENT
# =============================================================================

class WorkerAgent(Agent):
    """Worker agent."""

    def __init__(
        self,
        config: AgentConfig,
        handler: Optional[Callable[[AgentTask], Any]] = None
    ):
        super().__init__(config)
        self._handler = handler

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute task."""
        if self._handler:
            if asyncio.iscoroutinefunction(self._handler):
                return await self._handler(task)
            return self._handler(task)

        # Default: return payload
        return task.payload


# =============================================================================
# SUPERVISOR AGENT
# =============================================================================

class SupervisorAgent(Agent):
    """Supervisor agent."""

    def __init__(self, config: AgentConfig):
        config.role = AgentRole.SUPERVISOR
        super().__init__(config)
        self._subordinates: Dict[str, Agent] = {}

    def add_subordinate(self, agent: Agent) -> None:
        """Add subordinate agent."""
        self._subordinates[agent.agent_id] = agent

    def remove_subordinate(self, agent_id: str) -> bool:
        """Remove subordinate."""
        if agent_id in self._subordinates:
            del self._subordinates[agent_id]
            return True
        return False

    async def execute_task(self, task: AgentTask) -> Any:
        """Delegate task to subordinates."""
        # Find suitable subordinate
        for agent in self._subordinates.values():
            if agent.status == AgentStatus.IDLE:
                if await agent.accept_task(task):
                    return await agent.run_task(task)

        raise Exception("No available subordinates")

    async def broadcast(self, content: Dict[str, Any]) -> None:
        """Broadcast to all subordinates."""
        for agent in self._subordinates.values():
            message = AgentMessage(
                message_type=MessageType.BROADCAST,
                sender=self.agent_id,
                recipient=agent.agent_id,
                content=content
            )
            await agent.send_message(message)


# =============================================================================
# AGENT POOL
# =============================================================================

class AgentPool:
    """Pool of agents."""

    def __init__(
        self,
        name: str,
        min_agents: int = 1,
        max_agents: int = 10
    ):
        self.name = name
        self.min_agents = min_agents
        self.max_agents = max_agents
        self._agents: Dict[str, Agent] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def add_agent(self, agent: Agent) -> bool:
        """Add agent to pool."""
        if len(self._agents) >= self.max_agents:
            return False

        self._agents[agent.agent_id] = agent
        return True

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from pool."""
        if len(self._agents) <= self.min_agents:
            return False

        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    async def submit_task(self, task: AgentTask) -> str:
        """Submit task to pool."""
        await self._task_queue.put(task)
        return task.task_id

    def get_idle_agents(self) -> List[Agent]:
        """Get idle agents."""
        return [a for a in self._agents.values() if a.status == AgentStatus.IDLE]

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        agents = list(self._agents.values())

        return {
            "name": self.name,
            "total_agents": len(agents),
            "idle_agents": sum(1 for a in agents if a.status == AgentStatus.IDLE),
            "busy_agents": sum(1 for a in agents if a.status == AgentStatus.BUSY),
            "queue_size": self._task_queue.qsize()
        }


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Load balancer for agents."""

    def __init__(
        self,
        strategy: DistributionStrategy = DistributionStrategy.LEAST_BUSY
    ):
        self._strategy = strategy
        self._agents: List[Agent] = []
        self._round_robin_index = 0
        self._affinity: Dict[str, str] = {}

    def add_agent(self, agent: Agent) -> None:
        """Add agent."""
        self._agents.append(agent)

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent."""
        for i, agent in enumerate(self._agents):
            if agent.agent_id == agent_id:
                self._agents.pop(i)
                return True
        return False

    def select_agent(
        self,
        task: AgentTask
    ) -> Optional[Agent]:
        """Select agent for task."""
        if not self._agents:
            return None

        available = [
            a for a in self._agents
            if a.status != AgentStatus.STOPPED
            and len(a.current_tasks) < a.config.max_concurrent_tasks
        ]

        if not available:
            return None

        if self._strategy == DistributionStrategy.ROUND_ROBIN:
            return self._round_robin(available)

        elif self._strategy == DistributionStrategy.LEAST_BUSY:
            return self._least_busy(available)

        elif self._strategy == DistributionStrategy.RANDOM:
            return random.choice(available)

        elif self._strategy == DistributionStrategy.CAPABILITY_BASED:
            return self._capability_based(available, task)

        elif self._strategy == DistributionStrategy.AFFINITY:
            return self._affinity_based(available, task)

        return available[0]

    def _round_robin(self, agents: List[Agent]) -> Agent:
        """Round robin selection."""
        agent = agents[self._round_robin_index % len(agents)]
        self._round_robin_index += 1
        return agent

    def _least_busy(self, agents: List[Agent]) -> Agent:
        """Least busy selection."""
        return min(agents, key=lambda a: len(a.current_tasks))

    def _capability_based(
        self,
        agents: List[Agent],
        task: AgentTask
    ) -> Optional[Agent]:
        """Capability-based selection."""
        if not task.required_capabilities:
            return self._least_busy(agents)

        best_agent = None
        best_score = -1

        for agent in agents:
            score = 0
            for cap in agent.config.capabilities:
                if cap.name in task.required_capabilities:
                    score += cap.level

            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

    def _affinity_based(
        self,
        agents: List[Agent],
        task: AgentTask
    ) -> Optional[Agent]:
        """Affinity-based selection."""
        affinity_key = task.payload.get("affinity_key", "")

        if affinity_key and affinity_key in self._affinity:
            preferred_id = self._affinity[affinity_key]
            for agent in agents:
                if agent.agent_id == preferred_id:
                    return agent

        agent = self._least_busy(agents)

        if affinity_key:
            self._affinity[affinity_key] = agent.agent_id

        return agent


# =============================================================================
# MESSAGE BROKER
# =============================================================================

class MessageBroker:
    """Message broker for agents."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._topics: Dict[str, Set[str]] = defaultdict(set)
        self._message_history: List[AgentMessage] = []

    def register(self, agent: Agent) -> None:
        """Register agent."""
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        """Unregister agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]

        for subscribers in self._topics.values():
            subscribers.discard(agent_id)

    def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe to topic."""
        self._topics[topic].add(agent_id)

    def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe from topic."""
        self._topics[topic].discard(agent_id)

    async def send(
        self,
        sender: str,
        recipient: str,
        content: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST
    ) -> str:
        """Send message."""
        message = AgentMessage(
            message_type=message_type,
            sender=sender,
            recipient=recipient,
            content=content
        )

        if recipient in self._agents:
            await self._agents[recipient].send_message(message)

        self._message_history.append(message)
        return message.message_id

    async def publish(
        self,
        sender: str,
        topic: str,
        content: Dict[str, Any]
    ) -> int:
        """Publish to topic."""
        subscribers = self._topics.get(topic, set())
        count = 0

        for agent_id in subscribers:
            if agent_id in self._agents:
                message = AgentMessage(
                    message_type=MessageType.BROADCAST,
                    sender=sender,
                    recipient=agent_id,
                    content=content
                )
                await self._agents[agent_id].send_message(message)
                count += 1

        return count

    async def request_reply(
        self,
        sender: str,
        recipient: str,
        content: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        """Request-reply pattern."""
        request_id = await self.send(sender, recipient, content, MessageType.REQUEST)

        # Wait for reply (simplified)
        # In production, use proper correlation
        return None


# =============================================================================
# TASK SCHEDULER
# =============================================================================

class TaskScheduler:
    """Task scheduler for agents."""

    def __init__(self, load_balancer: LoadBalancer):
        self._load_balancer = load_balancer
        self._pending_tasks: List[AgentTask] = []
        self._running_tasks: Dict[str, AgentTask] = {}
        self._completed_tasks: List[AgentTask] = []

    def submit(self, task: AgentTask) -> str:
        """Submit task."""
        self._pending_tasks.append(task)
        self._sort_by_priority()
        return task.task_id

    def _sort_by_priority(self) -> None:
        """Sort pending tasks by priority."""
        self._pending_tasks.sort(
            key=lambda t: t.priority.value,
            reverse=True
        )

    async def schedule_next(self) -> Optional[AgentTask]:
        """Schedule next task."""
        if not self._pending_tasks:
            return None

        for i, task in enumerate(self._pending_tasks):
            agent = self._load_balancer.select_agent(task)

            if agent and await agent.accept_task(task):
                self._pending_tasks.pop(i)
                self._running_tasks[task.task_id] = task

                # Run task in background
                asyncio.create_task(self._run_task(agent, task))
                return task

        return None

    async def _run_task(self, agent: Agent, task: AgentTask) -> None:
        """Run task on agent."""
        try:
            await agent.run_task(task)
        except Exception as e:
            task.error = str(e)
        finally:
            if task.task_id in self._running_tasks:
                del self._running_tasks[task.task_id]
            self._completed_tasks.append(task)

    def get_pending_count(self) -> int:
        """Get pending count."""
        return len(self._pending_tasks)

    def get_running_count(self) -> int:
        """Get running count."""
        return len(self._running_tasks)


# =============================================================================
# AGENT ORCHESTRATOR
# =============================================================================

class AgentOrchestrator:
    """
    Agent Orchestrator for BAEL.

    Coordinates multiple AI agents.
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._pools: Dict[str, AgentPool] = {}
        self._load_balancer = LoadBalancer()
        self._message_broker = MessageBroker()
        self._task_scheduler = TaskScheduler(self._load_balancer)
        self._running = False

    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------

    def create_agent(
        self,
        name: str,
        role: str = "worker",
        capabilities: Optional[List[str]] = None,
        handler: Optional[Callable] = None
    ) -> Agent:
        """Create agent."""
        role_map = {
            "worker": AgentRole.WORKER,
            "supervisor": AgentRole.SUPERVISOR,
            "coordinator": AgentRole.COORDINATOR,
            "specialist": AgentRole.SPECIALIST
        }

        caps = [AgentCapability(name=c) for c in (capabilities or [])]

        config = AgentConfig(
            name=name,
            role=role_map.get(role.lower(), AgentRole.WORKER),
            capabilities=caps
        )

        if role.lower() == "supervisor":
            agent = SupervisorAgent(config)
        else:
            agent = WorkerAgent(config, handler)

        self._agents[agent.agent_id] = agent
        self._load_balancer.add_agent(agent)
        self._message_broker.register(agent)

        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent."""
        return self._agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent."""
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            agent.status = AgentStatus.STOPPED

            self._load_balancer.remove_agent(agent_id)
            self._message_broker.unregister(agent_id)

            del self._agents[agent_id]
            return True
        return False

    def list_agents(self) -> List[Dict[str, Any]]:
        """List agents."""
        return [
            {
                "id": a.agent_id,
                "name": a.name,
                "role": a.role.value,
                "status": a.status.value
            }
            for a in self._agents.values()
        ]

    # -------------------------------------------------------------------------
    # POOL MANAGEMENT
    # -------------------------------------------------------------------------

    def create_pool(
        self,
        name: str,
        min_agents: int = 1,
        max_agents: int = 10
    ) -> AgentPool:
        """Create agent pool."""
        pool = AgentPool(name, min_agents, max_agents)
        self._pools[name] = pool
        return pool

    def get_pool(self, name: str) -> Optional[AgentPool]:
        """Get pool."""
        return self._pools.get(name)

    def add_to_pool(self, pool_name: str, agent_id: str) -> bool:
        """Add agent to pool."""
        pool = self._pools.get(pool_name)
        agent = self._agents.get(agent_id)

        if pool and agent:
            return pool.add_agent(agent)
        return False

    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------

    def create_task(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: str = "medium",
        required_capabilities: Optional[List[str]] = None
    ) -> AgentTask:
        """Create task."""
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
            "background": TaskPriority.BACKGROUND
        }

        return AgentTask(
            name=name,
            payload=payload,
            priority=priority_map.get(priority.lower(), TaskPriority.MEDIUM),
            required_capabilities=required_capabilities or []
        )

    async def submit_task(self, task: AgentTask) -> str:
        """Submit task."""
        return self._task_scheduler.submit(task)

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute task immediately."""
        agent = self._load_balancer.select_agent(task)

        if not agent:
            raise Exception("No available agents")

        if not await agent.accept_task(task):
            raise Exception("Agent rejected task")

        return await agent.run_task(task)

    async def schedule_tasks(self, count: int = 10) -> int:
        """Schedule pending tasks."""
        scheduled = 0

        for _ in range(count):
            task = await self._task_scheduler.schedule_next()
            if task:
                scheduled += 1
            else:
                break

        return scheduled

    # -------------------------------------------------------------------------
    # MESSAGING
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: Dict[str, Any]
    ) -> str:
        """Send message."""
        return await self._message_broker.send(
            sender_id,
            recipient_id,
            content
        )

    async def broadcast(
        self,
        sender_id: str,
        topic: str,
        content: Dict[str, Any]
    ) -> int:
        """Broadcast to topic."""
        return await self._message_broker.publish(sender_id, topic, content)

    def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe agent to topic."""
        self._message_broker.subscribe(agent_id, topic)

    # -------------------------------------------------------------------------
    # SUPERVISION
    # -------------------------------------------------------------------------

    def set_supervisor(
        self,
        supervisor_id: str,
        subordinate_id: str
    ) -> bool:
        """Set supervision relationship."""
        supervisor = self._agents.get(supervisor_id)
        subordinate = self._agents.get(subordinate_id)

        if isinstance(supervisor, SupervisorAgent) and subordinate:
            supervisor.add_subordinate(subordinate)
            return True
        return False

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_agent_stats(self, agent_id: str) -> Optional[AgentStats]:
        """Get agent stats."""
        agent = self._agents.get(agent_id)
        if agent:
            return agent.get_stats()
        return None

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator stats."""
        agents = list(self._agents.values())

        return {
            "total_agents": len(agents),
            "idle_agents": sum(1 for a in agents if a.status == AgentStatus.IDLE),
            "busy_agents": sum(1 for a in agents if a.status == AgentStatus.BUSY),
            "pending_tasks": self._task_scheduler.get_pending_count(),
            "running_tasks": self._task_scheduler.get_running_count(),
            "pools": len(self._pools)
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

    agent1 = orchestrator.create_agent(
        name="Worker-1",
        role="worker",
        capabilities=["analysis", "processing"],
        handler=lambda t: {"processed": t.payload}
    )

    agent2 = orchestrator.create_agent(
        name="Worker-2",
        role="worker",
        capabilities=["analysis", "reporting"],
        handler=lambda t: {"analyzed": t.payload}
    )

    agent3 = orchestrator.create_agent(
        name="Supervisor-1",
        role="supervisor"
    )

    print(f"   Created: {agent1.name} ({agent1.agent_id[:8]}...)")
    print(f"   Created: {agent2.name} ({agent2.agent_id[:8]}...)")
    print(f"   Created: {agent3.name} ({agent3.agent_id[:8]}...)")
    print()

    # 2. List Agents
    print("2. LIST AGENTS:")
    print("-" * 40)

    agents = orchestrator.list_agents()
    for a in agents:
        print(f"   {a['name']}: {a['role']} - {a['status']}")
    print()

    # 3. Create Pool
    print("3. CREATE AGENT POOL:")
    print("-" * 40)

    pool = orchestrator.create_pool("workers", min_agents=1, max_agents=5)
    orchestrator.add_to_pool("workers", agent1.agent_id)
    orchestrator.add_to_pool("workers", agent2.agent_id)

    pool_stats = pool.get_stats()
    print(f"   Pool: {pool_stats['name']}")
    print(f"   Agents: {pool_stats['total_agents']}")
    print()

    # 4. Supervision
    print("4. SET SUPERVISION:")
    print("-" * 40)

    orchestrator.set_supervisor(agent3.agent_id, agent1.agent_id)
    orchestrator.set_supervisor(agent3.agent_id, agent2.agent_id)

    print(f"   {agent3.name} supervises:")
    print(f"     - {agent1.name}")
    print(f"     - {agent2.name}")
    print()

    # 5. Create and Execute Task
    print("5. EXECUTE TASK:")
    print("-" * 40)

    task = orchestrator.create_task(
        name="Analyze Data",
        payload={"data": [1, 2, 3, 4, 5]},
        priority="high",
        required_capabilities=["analysis"]
    )

    result = await orchestrator.execute_task(task)

    print(f"   Task: {task.name}")
    print(f"   Priority: {task.priority.value}")
    print(f"   Result: {result}")
    print()

    # 6. Submit Multiple Tasks
    print("6. SUBMIT MULTIPLE TASKS:")
    print("-" * 40)

    for i in range(5):
        task = orchestrator.create_task(
            name=f"Task-{i+1}",
            payload={"index": i},
            priority="medium"
        )
        await orchestrator.submit_task(task)

    pending = orchestrator._task_scheduler.get_pending_count()
    print(f"   Submitted: 5 tasks")
    print(f"   Pending: {pending}")
    print()

    # 7. Schedule Tasks
    print("7. SCHEDULE TASKS:")
    print("-" * 40)

    scheduled = await orchestrator.schedule_tasks(count=3)

    print(f"   Scheduled: {scheduled} tasks")
    await asyncio.sleep(0.1)  # Allow tasks to complete
    print()

    # 8. Messaging
    print("8. AGENT MESSAGING:")
    print("-" * 40)

    message_id = await orchestrator.send_message(
        agent1.agent_id,
        agent2.agent_id,
        {"action": "sync", "data": "test"}
    )

    print(f"   Message sent: {message_id[:8]}...")
    print(f"   From: {agent1.name}")
    print(f"   To: {agent2.name}")
    print()

    # 9. Topic Subscription
    print("9. TOPIC SUBSCRIPTION:")
    print("-" * 40)

    orchestrator.subscribe(agent1.agent_id, "updates")
    orchestrator.subscribe(agent2.agent_id, "updates")

    count = await orchestrator.broadcast(
        agent3.agent_id,
        "updates",
        {"notification": "System update"}
    )

    print(f"   Topic: updates")
    print(f"   Subscribers: 2")
    print(f"   Broadcast to: {count} agents")
    print()

    # 10. Agent Statistics
    print("10. AGENT STATISTICS:")
    print("-" * 40)

    stats = orchestrator.get_agent_stats(agent1.agent_id)

    if stats:
        print(f"   Agent: {agent1.name}")
        print(f"   Tasks completed: {stats.tasks_completed}")
        print(f"   Current tasks: {stats.current_tasks}")
        print(f"   Uptime: {stats.uptime:.2f}s")
    print()

    # 11. Orchestrator Statistics
    print("11. ORCHESTRATOR STATISTICS:")
    print("-" * 40)

    stats = orchestrator.get_orchestrator_stats()

    print(f"   Total agents: {stats['total_agents']}")
    print(f"   Idle: {stats['idle_agents']}")
    print(f"   Busy: {stats['busy_agents']}")
    print(f"   Pending tasks: {stats['pending_tasks']}")
    print(f"   Running tasks: {stats['running_tasks']}")
    print()

    # 12. Remove Agent
    print("12. REMOVE AGENT:")
    print("-" * 40)

    removed = orchestrator.remove_agent(agent2.agent_id)

    print(f"   Removed: {agent2.name} = {removed}")
    print(f"   Remaining agents: {len(orchestrator.list_agents())}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Agent Orchestrator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
