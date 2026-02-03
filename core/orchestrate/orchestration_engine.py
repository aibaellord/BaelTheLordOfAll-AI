#!/usr/bin/env python3
"""
BAEL - Orchestration Engine
Multi-agent coordination and distributed execution.

Features:
- Agent lifecycle management
- Task distribution
- Load balancing
- Fault tolerance
- Communication protocols
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MessageType(Enum):
    """Inter-agent message types."""
    TASK = "task"
    RESULT = "result"
    HEARTBEAT = "heartbeat"
    CONTROL = "control"
    BROADCAST = "broadcast"
    REQUEST = "request"
    RESPONSE = "response"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    AFFINITY = "affinity"


class FaultHandling(Enum):
    """Fault handling strategies."""
    RETRY = "retry"
    FAILOVER = "failover"
    CIRCUIT_BREAKER = "circuit_breaker"
    BULKHEAD = "bulkhead"


class CoordinationMode(Enum):
    """Coordination modes."""
    CENTRALIZED = "centralized"
    DISTRIBUTED = "distributed"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AgentConfig:
    """Agent configuration."""
    agent_id: str = ""
    name: str = ""
    agent_type: str = "worker"
    capabilities: List[str] = field(default_factory=list)
    max_concurrent: int = 4
    heartbeat_interval: float = 5.0
    timeout_seconds: float = 30.0
    weight: float = 1.0

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())[:8]


@dataclass
class AgentStatus:
    """Agent status."""
    agent_id: str
    state: AgentState = AgentState.IDLE
    current_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_heartbeat: Optional[datetime] = None
    uptime_seconds: float = 0.0


@dataclass
class Message:
    """Inter-agent message."""
    message_id: str = ""
    message_type: MessageType = MessageType.TASK
    sender_id: str = ""
    receiver_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: float = 60.0
    reply_to: Optional[str] = None

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]


@dataclass
class Task:
    """Orchestrated task."""
    task_id: str = ""
    name: str = ""
    handler: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retries: int = 0

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    agent_id: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class CircuitBreaker:
    """Circuit breaker state."""
    agent_id: str
    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    is_open: bool = False
    last_failure: Optional[datetime] = None


@dataclass
class OrchestrationStats:
    """Orchestration statistics."""
    total_agents: int = 0
    active_agents: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    messages_sent: int = 0
    by_agent: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# AGENT BASE
# =============================================================================

class BaseAgent(ABC):
    """Abstract base agent."""

    def __init__(self, config: AgentConfig):
        self._config = config
        self._state = AgentState.CREATED
        self._task_queue: deque = deque()
        self._results: Dict[str, TaskResult] = {}
        self._started_at: Optional[datetime] = None
        self._handlers: Dict[str, Callable] = {}

    @property
    def agent_id(self) -> str:
        return self._config.agent_id

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def capabilities(self) -> List[str]:
        return self._config.capabilities

    @abstractmethod
    async def start(self) -> None:
        """Start the agent."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the agent."""
        pass

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task."""
        pass

    def get_status(self) -> AgentStatus:
        """Get agent status."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()

        return AgentStatus(
            agent_id=self.agent_id,
            state=self._state,
            current_tasks=len(self._task_queue),
            completed_tasks=len([r for r in self._results.values() if r.success]),
            failed_tasks=len([r for r in self._results.values() if not r.success]),
            last_heartbeat=datetime.now(),
            uptime_seconds=uptime
        )

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a task handler."""
        self._handlers[name] = handler


class WorkerAgent(BaseAgent):
    """Worker agent implementation."""

    async def start(self) -> None:
        """Start the worker."""
        self._state = AgentState.STARTING
        self._started_at = datetime.now()
        await asyncio.sleep(0.01)
        self._state = AgentState.IDLE

    async def stop(self) -> None:
        """Stop the worker."""
        self._state = AgentState.STOPPING
        await asyncio.sleep(0.01)
        self._state = AgentState.STOPPED

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task."""
        self._state = AgentState.BUSY
        self._task_queue.append(task)

        start_time = time.time()
        result = TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id
        )

        try:
            handler = self._handlers.get(task.handler)

            if handler:
                if asyncio.iscoroutinefunction(handler):
                    output = await asyncio.wait_for(
                        handler(**task.params),
                        timeout=task.timeout_seconds
                    )
                else:
                    output = handler(**task.params)
            else:
                await asyncio.sleep(0.05)
                output = {"processed": True, **task.params}

            result.success = True
            result.result = output

        except asyncio.TimeoutError:
            result.success = False
            result.error = "Task timeout"

        except Exception as e:
            result.success = False
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000

        self._task_queue.popleft()
        self._results[task.task_id] = result

        if not self._task_queue:
            self._state = AgentState.IDLE

        return result


class SupervisorAgent(BaseAgent):
    """Supervisor agent for monitoring workers."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._workers: Dict[str, BaseAgent] = {}

    async def start(self) -> None:
        self._state = AgentState.STARTING
        self._started_at = datetime.now()

        for worker in self._workers.values():
            await worker.start()

        self._state = AgentState.IDLE

    async def stop(self) -> None:
        self._state = AgentState.STOPPING

        for worker in self._workers.values():
            await worker.stop()

        self._state = AgentState.STOPPED

    async def execute(self, task: Task) -> TaskResult:
        """Delegate to workers."""
        available = [
            w for w in self._workers.values()
            if w.state == AgentState.IDLE
        ]

        if not available:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No available workers"
            )

        worker = random.choice(available)
        return await worker.execute(task)

    def add_worker(self, worker: BaseAgent) -> None:
        """Add a worker."""
        self._workers[worker.agent_id] = worker


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Load balancer for task distribution."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self._strategy = strategy
        self._agents: Dict[str, AgentConfig] = {}
        self._current_index: int = 0
        self._affinity_map: Dict[str, str] = {}

    def register(self, config: AgentConfig) -> None:
        """Register an agent."""
        self._agents[config.agent_id] = config

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        self._agents.pop(agent_id, None)

    def select(
        self,
        task: Task,
        agent_statuses: Dict[str, AgentStatus]
    ) -> Optional[str]:
        """Select an agent for task."""
        available = self._get_available_agents(task, agent_statuses)

        if not available:
            return None

        if self._strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(available)

        elif self._strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(available)

        elif self._strategy == LoadBalanceStrategy.LEAST_LOADED:
            return self._least_loaded(available, agent_statuses)

        elif self._strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted(available)

        elif self._strategy == LoadBalanceStrategy.AFFINITY:
            return self._affinity(task, available)

        return available[0] if available else None

    def _get_available_agents(
        self,
        task: Task,
        statuses: Dict[str, AgentStatus]
    ) -> List[str]:
        """Get available agents for task."""
        available = []

        for agent_id, config in self._agents.items():
            status = statuses.get(agent_id)

            if not status or status.state not in (AgentState.IDLE, AgentState.BUSY):
                continue

            if status.current_tasks >= config.max_concurrent:
                continue

            if task.required_capabilities:
                if not all(cap in config.capabilities for cap in task.required_capabilities):
                    continue

            available.append(agent_id)

        return available

    def _round_robin(self, available: List[str]) -> str:
        """Round-robin selection."""
        self._current_index = (self._current_index + 1) % len(available)
        return available[self._current_index]

    def _least_loaded(
        self,
        available: List[str],
        statuses: Dict[str, AgentStatus]
    ) -> str:
        """Least-loaded selection."""
        return min(
            available,
            key=lambda aid: statuses.get(aid, AgentStatus(aid)).current_tasks
        )

    def _weighted(self, available: List[str]) -> str:
        """Weighted random selection."""
        weights = [self._agents[aid].weight for aid in available]
        total = sum(weights)

        r = random.uniform(0, total)
        cumulative = 0.0

        for aid, w in zip(available, weights):
            cumulative += w
            if r <= cumulative:
                return aid

        return available[-1]

    def _affinity(self, task: Task, available: List[str]) -> str:
        """Affinity-based selection."""
        affinity_key = task.handler

        if affinity_key in self._affinity_map:
            preferred = self._affinity_map[affinity_key]
            if preferred in available:
                return preferred

        selected = random.choice(available)
        self._affinity_map[affinity_key] = selected

        return selected


# =============================================================================
# MESSAGE BUS
# =============================================================================

class MessageBus:
    """Message bus for agent communication."""

    def __init__(self):
        self._queues: Dict[str, deque] = defaultdict(deque)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._broadcast_subscribers: List[Callable] = []
        self._messages_sent: int = 0

    async def send(self, message: Message) -> None:
        """Send a message."""
        self._queues[message.receiver_id].append(message)
        self._messages_sent += 1

        for callback in self._subscribers.get(message.receiver_id, []):
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)

    async def broadcast(self, message: Message) -> None:
        """Broadcast a message."""
        message.message_type = MessageType.BROADCAST

        for callback in self._broadcast_subscribers:
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)

        self._messages_sent += 1

    def receive(self, agent_id: str) -> Optional[Message]:
        """Receive a message."""
        queue = self._queues.get(agent_id)

        if queue:
            return queue.popleft()

        return None

    def peek(self, agent_id: str) -> Optional[Message]:
        """Peek at next message."""
        queue = self._queues.get(agent_id)

        if queue:
            return queue[0]

        return None

    def subscribe(self, agent_id: str, callback: Callable) -> None:
        """Subscribe to messages."""
        self._subscribers[agent_id].append(callback)

    def subscribe_broadcast(self, callback: Callable) -> None:
        """Subscribe to broadcasts."""
        self._broadcast_subscribers.append(callback)

    def pending_count(self, agent_id: str) -> int:
        """Get pending message count."""
        return len(self._queues.get(agent_id, []))

    @property
    def messages_sent(self) -> int:
        return self._messages_sent


# =============================================================================
# FAULT HANDLER
# =============================================================================

class FaultHandler:
    """Handle faults and failures."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_counts: Dict[str, int] = defaultdict(int)
        self._max_retries: int = 3

    def get_circuit_breaker(self, agent_id: str) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if agent_id not in self._circuit_breakers:
            self._circuit_breakers[agent_id] = CircuitBreaker(agent_id=agent_id)

        return self._circuit_breakers[agent_id]

    def record_success(self, agent_id: str) -> None:
        """Record successful execution."""
        cb = self.get_circuit_breaker(agent_id)
        cb.failure_count = 0
        cb.is_open = False

    def record_failure(self, agent_id: str) -> None:
        """Record failed execution."""
        cb = self.get_circuit_breaker(agent_id)
        cb.failure_count += 1
        cb.last_failure = datetime.now()

        if cb.failure_count >= cb.failure_threshold:
            cb.is_open = True

    def is_available(self, agent_id: str) -> bool:
        """Check if agent is available."""
        cb = self.get_circuit_breaker(agent_id)

        if not cb.is_open:
            return True

        if cb.last_failure:
            elapsed = (datetime.now() - cb.last_failure).total_seconds()
            if elapsed >= cb.recovery_timeout:
                cb.is_open = False
                return True

        return False

    def should_retry(self, task_id: str) -> bool:
        """Check if task should be retried."""
        count = self._retry_counts[task_id]
        return count < self._max_retries

    def increment_retry(self, task_id: str) -> int:
        """Increment retry count."""
        self._retry_counts[task_id] += 1
        return self._retry_counts[task_id]


# =============================================================================
# ORCHESTRATION ENGINE
# =============================================================================

class OrchestrationEngine:
    """
    Orchestration Engine for BAEL.

    Multi-agent coordination and distributed execution.
    """

    def __init__(
        self,
        mode: CoordinationMode = CoordinationMode.CENTRALIZED,
        load_balance: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    ):
        self._mode = mode

        self._agents: Dict[str, BaseAgent] = {}
        self._load_balancer = LoadBalancer(load_balance)
        self._message_bus = MessageBus()
        self._fault_handler = FaultHandler()

        self._task_queue: deque = deque()
        self._results: Dict[str, TaskResult] = {}

        self._stats = OrchestrationStats()
        self._running = False

    async def register_agent(
        self,
        name: str,
        agent_type: str = "worker",
        capabilities: Optional[List[str]] = None,
        max_concurrent: int = 4,
        weight: float = 1.0
    ) -> BaseAgent:
        """Register and start an agent."""
        config = AgentConfig(
            name=name,
            agent_type=agent_type,
            capabilities=capabilities or [],
            max_concurrent=max_concurrent,
            weight=weight
        )

        if agent_type == "supervisor":
            agent = SupervisorAgent(config)
        else:
            agent = WorkerAgent(config)

        await agent.start()

        self._agents[agent.agent_id] = agent
        self._load_balancer.register(config)

        self._stats.total_agents += 1
        self._stats.active_agents += 1

        return agent

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister and stop an agent."""
        agent = self._agents.pop(agent_id, None)

        if agent:
            await agent.stop()
            self._load_balancer.unregister(agent_id)
            self._stats.active_agents -= 1

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentStatus]:
        """List all agent statuses."""
        return [agent.get_status() for agent in self._agents.values()]

    async def submit_task(
        self,
        name: str,
        handler: str = "default",
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        capabilities: Optional[List[str]] = None
    ) -> str:
        """Submit a task for execution."""
        task = Task(
            name=name,
            handler=handler,
            params=params or {},
            priority=priority,
            required_capabilities=capabilities or []
        )

        self._task_queue.append(task)
        self._stats.total_tasks += 1

        return task.task_id

    async def execute_task(self, task_id: str) -> Optional[TaskResult]:
        """Execute a specific task."""
        task = None

        for t in self._task_queue:
            if t.task_id == task_id:
                task = t
                break

        if not task:
            return None

        statuses = {aid: a.get_status() for aid, a in self._agents.items()}

        agent_id = self._load_balancer.select(task, statuses)

        if not agent_id:
            return TaskResult(
                task_id=task.task_id,
                agent_id="",
                success=False,
                error="No available agents"
            )

        if not self._fault_handler.is_available(agent_id):
            agent_id = self._load_balancer.select(task, statuses)

        agent = self._agents.get(agent_id)
        if not agent:
            return None

        task.assigned_agent = agent_id

        result = await agent.execute(task)

        if result.success:
            self._fault_handler.record_success(agent_id)
            self._stats.completed_tasks += 1
        else:
            self._fault_handler.record_failure(agent_id)

            if self._fault_handler.should_retry(task_id):
                self._fault_handler.increment_retry(task_id)
                return await self.execute_task(task_id)

            self._stats.failed_tasks += 1

        self._results[task_id] = result
        self._stats.by_agent[agent_id] = self._stats.by_agent.get(agent_id, 0) + 1

        return result

    async def process_queue(self) -> List[TaskResult]:
        """Process all queued tasks."""
        results = []

        while self._task_queue:
            task = self._task_queue.popleft()
            result = await self.execute_task(task.task_id)

            if result:
                results.append(result)

        return results

    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.TASK
    ) -> str:
        """Send a message between agents."""
        message = Message(
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=payload
        )

        await self._message_bus.send(message)
        self._stats.messages_sent += 1

        return message.message_id

    async def broadcast(
        self,
        sender_id: str,
        payload: Dict[str, Any]
    ) -> str:
        """Broadcast a message to all agents."""
        message = Message(
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            payload=payload
        )

        await self._message_bus.broadcast(message)
        self._stats.messages_sent += 1

        return message.message_id

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result."""
        return self._results.get(task_id)

    @property
    def stats(self) -> OrchestrationStats:
        """Get orchestration statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "mode": self._mode.value,
            "agents": {
                "total": self._stats.total_agents,
                "active": self._stats.active_agents
            },
            "tasks": {
                "total": self._stats.total_tasks,
                "completed": self._stats.completed_tasks,
                "failed": self._stats.failed_tasks,
                "pending": len(self._task_queue)
            },
            "messages_sent": self._stats.messages_sent,
            "by_agent": self._stats.by_agent
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Orchestration Engine."""
    print("=" * 70)
    print("BAEL - ORCHESTRATION ENGINE DEMO")
    print("Multi-Agent Coordination")
    print("=" * 70)
    print()

    engine = OrchestrationEngine(
        mode=CoordinationMode.CENTRALIZED,
        load_balance=LoadBalanceStrategy.ROUND_ROBIN
    )

    # 1. Register Agents
    print("1. REGISTER AGENTS:")
    print("-" * 40)

    worker1 = await engine.register_agent(
        name="Worker-1",
        capabilities=["compute", "transform"],
        max_concurrent=4
    )

    worker2 = await engine.register_agent(
        name="Worker-2",
        capabilities=["compute", "io"],
        max_concurrent=4
    )

    worker3 = await engine.register_agent(
        name="Worker-3",
        capabilities=["transform", "io"],
        max_concurrent=4
    )

    print(f"   Registered: {worker1.name} ({worker1.agent_id})")
    print(f"   Registered: {worker2.name} ({worker2.agent_id})")
    print(f"   Registered: {worker3.name} ({worker3.agent_id})")
    print()

    # 2. List Agents
    print("2. LIST AGENTS:")
    print("-" * 40)

    statuses = engine.list_agents()

    for status in statuses:
        print(f"   {status.agent_id}: {status.state.value}")
    print()

    # 3. Submit Tasks
    print("3. SUBMIT TASKS:")
    print("-" * 40)

    task_ids = []

    for i in range(5):
        task_id = await engine.submit_task(
            name=f"Task-{i+1}",
            handler="process",
            params={"data": f"item-{i+1}"}
        )
        task_ids.append(task_id)
        print(f"   Submitted: Task-{i+1} ({task_id})")
    print()

    # 4. Process Queue
    print("4. PROCESS QUEUE:")
    print("-" * 40)

    results = await engine.process_queue()

    for result in results:
        status = "✓" if result.success else "✗"
        print(f"   {status} Task {result.task_id}: {result.duration_ms:.2f}ms")
    print()

    # 5. Agent Status After Execution
    print("5. AGENT STATUS AFTER EXECUTION:")
    print("-" * 40)

    statuses = engine.list_agents()

    for status in statuses:
        print(f"   {status.agent_id}:")
        print(f"      State: {status.state.value}")
        print(f"      Completed: {status.completed_tasks}")
    print()

    # 6. Send Messages
    print("6. SEND MESSAGES:")
    print("-" * 40)

    msg_id = await engine.send_message(
        sender_id=worker1.agent_id,
        receiver_id=worker2.agent_id,
        payload={"action": "sync", "data": [1, 2, 3]}
    )
    print(f"   Message sent: {msg_id}")

    broadcast_id = await engine.broadcast(
        sender_id=worker1.agent_id,
        payload={"announcement": "System update"}
    )
    print(f"   Broadcast: {broadcast_id}")
    print()

    # 7. Task with Required Capabilities
    print("7. CAPABILITY-BASED ROUTING:")
    print("-" * 40)

    io_task = await engine.submit_task(
        name="IO-Task",
        handler="io_process",
        capabilities=["io"]
    )

    await engine.execute_task(io_task)
    result = engine.get_result(io_task)

    print(f"   IO Task assigned to: {result.agent_id if result else 'N/A'}")
    print()

    # 8. Get Result
    print("8. GET RESULT:")
    print("-" * 40)

    if task_ids:
        result = engine.get_result(task_ids[0])

        if result:
            print(f"   Task ID: {result.task_id}")
            print(f"   Agent: {result.agent_id}")
            print(f"   Success: {result.success}")
            print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 9. Statistics
    print("9. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Agents: {stats.total_agents}")
    print(f"   Active Agents: {stats.active_agents}")
    print(f"   Total Tasks: {stats.total_tasks}")
    print(f"   Completed: {stats.completed_tasks}")
    print(f"   Failed: {stats.failed_tasks}")
    print(f"   Messages Sent: {stats.messages_sent}")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Mode: {summary['mode']}")
    print(f"   Agents: {summary['agents']}")
    print(f"   Tasks: {summary['tasks']}")
    print(f"   By Agent: {summary['by_agent']}")
    print()

    # Cleanup
    print("11. CLEANUP:")
    print("-" * 40)

    for agent_id in list(engine._agents.keys()):
        await engine.unregister_agent(agent_id)
        print(f"   Unregistered: {agent_id}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Orchestration Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
