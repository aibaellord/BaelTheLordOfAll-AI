"""
BAEL - Advanced Agent Orchestration
Sophisticated multi-agent orchestration with complex workflows.

Features:
- Agent lifecycle management
- Dynamic agent spawning
- Complex workflow orchestration
- Agent supervision and recovery
- Load balancing
- Agent pools
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DEAD = "dead"


class SupervisionStrategy(Enum):
    """How to handle agent failures."""
    ONE_FOR_ONE = "one_for_one"  # Restart only failed agent
    ONE_FOR_ALL = "one_for_all"  # Restart all agents
    REST_FOR_ONE = "rest_for_one"  # Restart failed and subsequent agents
    ESCALATE = "escalate"  # Escalate to parent supervisor


class RestartStrategy(Enum):
    """How to restart failed agents."""
    PERMANENT = "permanent"  # Always restart
    TEMPORARY = "temporary"  # Never restart
    TRANSIENT = "transient"  # Restart only on abnormal exit


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentSpec:
    """Specification for creating an agent."""
    id: str
    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    restart_strategy: RestartStrategy = RestartStrategy.PERMANENT
    max_restarts: int = 3
    restart_window: float = 60.0  # seconds
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentInfo:
    """Runtime information about an agent."""
    id: str
    name: str
    type: str
    state: AgentState
    created_at: float
    started_at: Optional[float] = None
    stopped_at: Optional[float] = None
    restarts: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpec:
    """Specification for a task."""
    id: str
    name: str
    payload: Any
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 300.0
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    assigned_to: Optional[str] = None


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    agent_id: Optional[str] = None


# =============================================================================
# AGENT BASE
# =============================================================================

class Agent(ABC):
    """Base class for all agents."""

    def __init__(self, spec: AgentSpec):
        self.id = spec.id
        self.name = spec.name
        self.config = spec.config
        self.state = AgentState.CREATED
        self._task: Optional[asyncio.Task] = None
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def setup(self) -> None:
        """Setup agent resources."""
        pass

    @abstractmethod
    async def run(self) -> None:
        """Main agent loop."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Cleanup agent resources."""
        pass

    async def start(self) -> None:
        """Start the agent."""
        if self.state != AgentState.CREATED and self.state != AgentState.STOPPED:
            return

        self.state = AgentState.STARTING

        try:
            await self.setup()
            self.state = AgentState.RUNNING
            self._task = asyncio.create_task(self._run_loop())
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.id} failed to start: {e}")
            raise

    async def _run_loop(self) -> None:
        """Internal run loop with error handling."""
        try:
            await self.run()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.id} error: {e}")
            raise
        finally:
            self.state = AgentState.STOPPED

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the agent."""
        if self.state not in (AgentState.RUNNING, AgentState.PAUSED):
            return

        self.state = AgentState.STOPPING
        self._stop_event.set()

        if self._task:
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._task),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self._task.cancel()

        try:
            await self.teardown()
        except Exception as e:
            logger.error(f"Agent {self.id} teardown error: {e}")

        self.state = AgentState.STOPPED

    async def send(self, message: Any) -> None:
        """Send message to agent inbox."""
        await self._inbox.put(message)

    async def receive(self, timeout: Optional[float] = None) -> Any:
        """Receive message from inbox."""
        if timeout:
            return await asyncio.wait_for(
                self._inbox.get(),
                timeout=timeout
            )
        return await self._inbox.get()

    def should_stop(self) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()


# =============================================================================
# WORKER AGENT
# =============================================================================

class WorkerAgent(Agent):
    """Agent that processes tasks from a queue."""

    def __init__(self, spec: AgentSpec, task_handler: Callable):
        super().__init__(spec)
        self._task_handler = task_handler
        self._current_task: Optional[TaskSpec] = None
        self._tasks_completed = 0

    async def setup(self) -> None:
        logger.info(f"Worker {self.id} setting up")

    async def run(self) -> None:
        """Process tasks from inbox."""
        while not self.should_stop():
            try:
                # Get task with timeout
                task = await asyncio.wait_for(
                    self.receive(),
                    timeout=1.0
                )

                if isinstance(task, TaskSpec):
                    self._current_task = task
                    result = await self._execute_task(task)
                    self._current_task = None
                    self._tasks_completed += 1

                    # Send result back
                    if hasattr(self, '_result_callback'):
                        await self._result_callback(result)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _execute_task(self, task: TaskSpec) -> TaskResult:
        """Execute a single task."""
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._task_handler(task.payload),
                timeout=task.timeout
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                execution_time=time.time() - start_time,
                agent_id=self.id
            )

        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Task timeout",
                execution_time=time.time() - start_time,
                agent_id=self.id
            )

        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                agent_id=self.id
            )

    async def teardown(self) -> None:
        logger.info(f"Worker {self.id} completed {self._tasks_completed} tasks")


# =============================================================================
# AGENT SUPERVISOR
# =============================================================================

class Supervisor:
    """Supervises a group of agents."""

    def __init__(
        self,
        name: str,
        strategy: SupervisionStrategy = SupervisionStrategy.ONE_FOR_ONE,
        max_restarts: int = 10,
        restart_window: float = 60.0
    ):
        self.name = name
        self.strategy = strategy
        self.max_restarts = max_restarts
        self.restart_window = restart_window

        self._agents: Dict[str, Agent] = {}
        self._specs: Dict[str, AgentSpec] = {}
        self._restart_history: List[float] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def add_agent(self, spec: AgentSpec, agent: Agent) -> None:
        """Add agent to supervision."""
        self._specs[spec.id] = spec
        self._agents[spec.id] = agent

    async def start(self) -> None:
        """Start all agents."""
        self._running = True

        # Start agents respecting dependencies
        started = set()

        while len(started) < len(self._agents):
            for agent_id, spec in self._specs.items():
                if agent_id in started:
                    continue

                # Check dependencies
                deps_met = all(
                    d in started for d in spec.dependencies
                )

                if deps_met:
                    await self._start_agent(agent_id)
                    started.add(agent_id)

        # Start monitoring
        self._monitor_task = asyncio.create_task(self._monitor())

    async def _start_agent(self, agent_id: str) -> None:
        """Start a single agent."""
        agent = self._agents.get(agent_id)
        if agent:
            try:
                await agent.start()
                logger.info(f"Started agent: {agent_id}")
            except Exception as e:
                logger.error(f"Failed to start agent {agent_id}: {e}")
                await self._handle_failure(agent_id)

    async def stop(self) -> None:
        """Stop all agents."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()

        # Stop in reverse dependency order
        for agent_id in reversed(list(self._agents.keys())):
            agent = self._agents[agent_id]
            await agent.stop()
            logger.info(f"Stopped agent: {agent_id}")

    async def _monitor(self) -> None:
        """Monitor agents and handle failures."""
        while self._running:
            await asyncio.sleep(1.0)

            for agent_id, agent in self._agents.items():
                if agent.state in (AgentState.ERROR, AgentState.DEAD):
                    await self._handle_failure(agent_id)

    async def _handle_failure(self, agent_id: str) -> None:
        """Handle agent failure based on strategy."""
        spec = self._specs.get(agent_id)
        if not spec:
            return

        # Check restart limits
        now = time.time()
        self._restart_history = [
            t for t in self._restart_history
            if now - t < self.restart_window
        ]

        if len(self._restart_history) >= self.max_restarts:
            logger.error(f"Supervisor {self.name} max restarts exceeded")
            if self.strategy == SupervisionStrategy.ESCALATE:
                raise RuntimeError(f"Supervisor {self.name} failed")
            return

        # Apply strategy
        if self.strategy == SupervisionStrategy.ONE_FOR_ONE:
            await self._restart_agent(agent_id)

        elif self.strategy == SupervisionStrategy.ONE_FOR_ALL:
            await self._restart_all()

        elif self.strategy == SupervisionStrategy.REST_FOR_ONE:
            await self._restart_from(agent_id)

        self._restart_history.append(now)

    async def _restart_agent(self, agent_id: str) -> None:
        """Restart a single agent."""
        spec = self._specs[agent_id]
        agent = self._agents[agent_id]

        # Check agent restart policy
        if spec.restart_strategy == RestartStrategy.TEMPORARY:
            return

        try:
            await agent.stop()
        except Exception:
            pass

        # Create new instance (simplified - in real use, factory pattern)
        logger.info(f"Restarting agent: {agent_id}")
        await self._start_agent(agent_id)

    async def _restart_all(self) -> None:
        """Restart all agents."""
        await self.stop()
        await self.start()

    async def _restart_from(self, agent_id: str) -> None:
        """Restart agent and all started after it."""
        agent_ids = list(self._agents.keys())
        idx = agent_ids.index(agent_id)

        # Stop from end to failed
        for aid in reversed(agent_ids[idx:]):
            agent = self._agents[aid]
            await agent.stop()

        # Restart from failed to end
        for aid in agent_ids[idx:]:
            await self._start_agent(aid)

    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status."""
        return {
            "name": self.name,
            "strategy": self.strategy.value,
            "running": self._running,
            "agents": {
                aid: {
                    "state": agent.state.value,
                    "name": agent.name
                }
                for aid, agent in self._agents.items()
            },
            "recent_restarts": len(self._restart_history)
        }


# =============================================================================
# AGENT POOL
# =============================================================================

class AgentPool:
    """Pool of worker agents for task distribution."""

    def __init__(
        self,
        name: str,
        size: int,
        agent_factory: Callable[[AgentSpec], Agent],
        task_handler: Callable
    ):
        self.name = name
        self.size = size
        self._factory = agent_factory
        self._task_handler = task_handler

        self._agents: List[WorkerAgent] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: Dict[str, TaskResult] = {}
        self._running = False
        self._distributor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the agent pool."""
        self._running = True

        # Create agents
        for i in range(self.size):
            spec = AgentSpec(
                id=f"{self.name}_worker_{i}",
                name=f"Worker {i}",
                type="worker"
            )

            agent = WorkerAgent(spec, self._task_handler)
            agent._result_callback = self._handle_result

            await agent.start()
            self._agents.append(agent)
            await self._available.put(agent)

        # Start distributor
        self._distributor_task = asyncio.create_task(self._distribute())
        logger.info(f"Started pool {self.name} with {self.size} workers")

    async def stop(self) -> None:
        """Stop the agent pool."""
        self._running = False

        if self._distributor_task:
            self._distributor_task.cancel()

        for agent in self._agents:
            await agent.stop()

        self._agents.clear()
        logger.info(f"Stopped pool {self.name}")

    async def submit(
        self,
        payload: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0
    ) -> str:
        """Submit task to pool."""
        task = TaskSpec(
            id=str(uuid.uuid4()),
            name=f"Task",
            payload=payload,
            priority=priority,
            timeout=timeout
        )

        # Priority queue uses (priority, timestamp, task)
        await self._task_queue.put(
            (-priority.value, time.time(), task)
        )

        return task.id

    async def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[TaskResult]:
        """Get task result."""
        start = time.time()

        while True:
            if task_id in self._results:
                return self._results.pop(task_id)

            if timeout and time.time() - start > timeout:
                return None

            await asyncio.sleep(0.1)

    async def _distribute(self) -> None:
        """Distribute tasks to workers."""
        while self._running:
            try:
                # Get task
                _, _, task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )

                # Get available worker
                worker = await self._available.get()

                # Assign task
                task.assigned_to = worker.id
                await worker.send(task)

                # Return worker to pool after task
                asyncio.create_task(self._return_worker(worker))

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _return_worker(self, worker: WorkerAgent) -> None:
        """Return worker to available pool."""
        # Wait for worker to finish current task
        while worker._current_task is not None:
            await asyncio.sleep(0.1)
        await self._available.put(worker)

    async def _handle_result(self, result: TaskResult) -> None:
        """Handle task result."""
        self._results[result.task_id] = result

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "name": self.name,
            "size": self.size,
            "running": self._running,
            "available_workers": self._available.qsize(),
            "pending_tasks": self._task_queue.qsize(),
            "completed_results": len(self._results)
        }


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class Orchestrator:
    """High-level agent orchestrator."""

    def __init__(self, name: str = "bael"):
        self.name = name
        self._supervisors: Dict[str, Supervisor] = {}
        self._pools: Dict[str, AgentPool] = {}
        self._agents: Dict[str, Agent] = {}
        self._running = False

    def add_supervisor(self, supervisor: Supervisor) -> None:
        """Add a supervisor."""
        self._supervisors[supervisor.name] = supervisor

    def add_pool(self, pool: AgentPool) -> None:
        """Add an agent pool."""
        self._pools[pool.name] = pool

    def add_agent(self, agent: Agent) -> None:
        """Add standalone agent."""
        self._agents[agent.id] = agent

    async def start(self) -> None:
        """Start the orchestrator."""
        self._running = True
        logger.info(f"Starting orchestrator: {self.name}")

        # Start supervisors
        for supervisor in self._supervisors.values():
            await supervisor.start()

        # Start pools
        for pool in self._pools.values():
            await pool.start()

        # Start standalone agents
        for agent in self._agents.values():
            await agent.start()

        logger.info(f"Orchestrator {self.name} started")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False
        logger.info(f"Stopping orchestrator: {self.name}")

        # Stop in reverse order
        for agent in self._agents.values():
            await agent.stop()

        for pool in self._pools.values():
            await pool.stop()

        for supervisor in self._supervisors.values():
            await supervisor.stop()

        logger.info(f"Orchestrator {self.name} stopped")

    def get_pool(self, name: str) -> Optional[AgentPool]:
        """Get agent pool by name."""
        return self._pools.get(name)

    def get_supervisor(self, name: str) -> Optional[Supervisor]:
        """Get supervisor by name."""
        return self._supervisors.get(name)

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "name": self.name,
            "running": self._running,
            "supervisors": {
                name: sup.get_status()
                for name, sup in self._supervisors.items()
            },
            "pools": {
                name: pool.get_stats()
                for name, pool in self._pools.items()
            },
            "standalone_agents": {
                aid: agent.state.value
                for aid, agent in self._agents.items()
            }
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

class SimpleWorker(Agent):
    """Simple example worker."""

    async def setup(self):
        logger.info(f"Setting up {self.name}")

    async def run(self):
        while not self.should_stop():
            try:
                msg = await asyncio.wait_for(self.receive(), timeout=1.0)
                logger.info(f"{self.name} received: {msg}")
            except asyncio.TimeoutError:
                continue

    async def teardown(self):
        logger.info(f"Tearing down {self.name}")


async def main():
    """Demonstrate agent orchestration."""
    logging.basicConfig(level=logging.INFO)

    print("=== BAEL Agent Orchestration ===\n")

    # Create orchestrator
    orchestrator = Orchestrator("demo")

    # Create supervisor with agents
    supervisor = Supervisor(
        "workers",
        strategy=SupervisionStrategy.ONE_FOR_ONE
    )

    for i in range(3):
        spec = AgentSpec(
            id=f"worker_{i}",
            name=f"Worker {i}",
            type="simple"
        )
        agent = SimpleWorker(spec)
        supervisor.add_agent(spec, agent)

    orchestrator.add_supervisor(supervisor)

    # Create worker pool
    async def process_task(payload: Dict) -> Any:
        """Process a task."""
        await asyncio.sleep(0.5)  # Simulate work
        return {"processed": payload, "result": "success"}

    pool = AgentPool(
        "task_pool",
        size=3,
        agent_factory=lambda spec: WorkerAgent(spec, process_task),
        task_handler=process_task
    )

    orchestrator.add_pool(pool)

    # Start orchestrator
    print("Starting orchestrator...")
    await orchestrator.start()

    await asyncio.sleep(1)

    # Submit tasks to pool
    print("\nSubmitting tasks to pool...")
    task_pool = orchestrator.get_pool("task_pool")

    task_ids = []
    for i in range(5):
        task_id = await task_pool.submit(
            {"task_num": i, "data": f"Task {i} data"},
            priority=TaskPriority.NORMAL
        )
        task_ids.append(task_id)
        print(f"Submitted task: {task_id[:8]}...")

    # Wait for results
    print("\nWaiting for results...")
    for task_id in task_ids:
        result = await task_pool.get_result(task_id, timeout=10.0)
        if result:
            print(f"Task {task_id[:8]}: {result.success} - {result.result}")

    # Get status
    print("\n=== Orchestrator Status ===")
    status = orchestrator.get_status()
    print(f"Running: {status['running']}")
    print(f"Supervisors: {list(status['supervisors'].keys())}")
    print(f"Pools: {list(status['pools'].keys())}")

    pool_stats = status['pools']['task_pool']
    print(f"\nTask Pool Stats:")
    print(f"  Workers: {pool_stats['size']}")
    print(f"  Available: {pool_stats['available_workers']}")
    print(f"  Pending: {pool_stats['pending_tasks']}")

    # Stop orchestrator
    print("\nStopping orchestrator...")
    await orchestrator.stop()

    print("\nOrchestration demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
