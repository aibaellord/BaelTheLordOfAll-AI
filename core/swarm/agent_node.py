"""
BAEL Agent Node
================

Individual agent node for swarm participation.
Autonomous agent that operates within a swarm.

Features:
- Autonomous task execution
- Swarm communication
- Self-monitoring
- Capability registration
- Adaptive behavior
"""

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles in swarm."""
    WORKER = "worker"  # General task execution
    SPECIALIST = "specialist"  # Domain-specific tasks
    SCOUT = "scout"  # Information gathering
    COORDINATOR = "coordinator"  # Sub-swarm coordination
    VALIDATOR = "validator"  # Result validation
    OPTIMIZER = "optimizer"  # Performance optimization


class NodeStatus(Enum):
    """Agent node status."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    WORKING = "working"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentCapability:
    """Agent capability definition."""
    name: str
    proficiency: float = 1.0  # 0.0 to 1.0

    # Resource requirements
    cpu_intensive: bool = False
    memory_mb: int = 0

    # Metadata
    description: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool

    # Output
    result: Any = None
    error: Optional[str] = None

    # Metrics
    execution_time_ms: float = 0.0
    resources_used: Dict[str, float] = field(default_factory=dict)

    # Metadata
    completed_at: datetime = field(default_factory=datetime.now)


class AgentNode:
    """
    Individual agent node for BAEL swarm.

    Operates autonomously within a coordinated swarm.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        role: AgentRole = AgentRole.WORKER,
    ):
        self.agent_id = agent_id or hashlib.md5(
            f"agent_{datetime.now()}_{random.random()}".encode()
        ).hexdigest()[:12]

        self.role = role
        self.status = NodeStatus.INITIALIZING

        # Capabilities
        self._capabilities: Dict[str, AgentCapability] = {}

        # Task handlers
        self._task_handlers: Dict[str, Callable] = {}

        # Message queue
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._outbox: asyncio.Queue = asyncio.Queue()

        # Current work
        self._current_task: Optional[Dict] = None
        self._task_history: List[TaskResult] = []

        # Connection to coordinator
        self._coordinator_queue: Optional[asyncio.Queue] = None

        # State
        self._running = False
        self._load = 0.0

        # Stats
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "uptime_seconds": 0,
        }

        self._started_at: Optional[datetime] = None

    def register_capability(
        self,
        name: str,
        proficiency: float = 1.0,
        **kwargs: Any,
    ) -> None:
        """Register a capability."""
        self._capabilities[name] = AgentCapability(
            name=name,
            proficiency=proficiency,
            **kwargs,
        )
        logger.debug(f"Agent {self.agent_id}: Registered capability {name}")

    def register_handler(
        self,
        task_type: str,
        handler: Callable,
    ) -> None:
        """Register task handler."""
        self._task_handlers[task_type] = handler
        logger.debug(f"Agent {self.agent_id}: Registered handler for {task_type}")

    def handler(self, task_type: str):
        """Decorator to register task handler."""
        def decorator(func: Callable):
            self.register_handler(task_type, func)
            return func
        return decorator

    async def start(self) -> None:
        """Start the agent node."""
        self._running = True
        self._started_at = datetime.now()
        self.status = NodeStatus.IDLE

        logger.info(f"Agent {self.agent_id} started as {self.role.value}")

        # Start processing loops
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._heartbeat_sender())

    async def stop(self) -> None:
        """Stop the agent node."""
        self._running = False
        self.status = NodeStatus.OFFLINE

        if self._started_at:
            self.stats["uptime_seconds"] = (
                datetime.now() - self._started_at
            ).total_seconds()

        logger.info(f"Agent {self.agent_id} stopped")

    async def connect_to_swarm(
        self,
        coordinator_queue: asyncio.Queue,
    ) -> None:
        """Connect to swarm coordinator."""
        self._coordinator_queue = coordinator_queue

        # Send registration
        await self._send_to_coordinator({
            "type": "register",
            "agent_id": self.agent_id,
            "role": self.role.value,
            "capabilities": list(self._capabilities.keys()),
        })

    async def _message_processor(self) -> None:
        """Process incoming messages."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._inbox.get(),
                    timeout=1.0,
                )

                self.stats["messages_received"] += 1
                await self._handle_message(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processor error: {e}")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming message."""
        msg_type = message.get("type", "")

        if msg_type == "heartbeat":
            # Respond to heartbeat
            await self._send_to_coordinator({
                "type": "heartbeat_ack",
                "agent_id": self.agent_id,
                "status": self.status.value,
                "load": self._load,
            })

        elif msg_type == "task":
            # Execute task
            await self._execute_task(message)

        elif msg_type == "broadcast":
            # Handle broadcast message
            logger.debug(f"Agent {self.agent_id} received broadcast: {message.get('msg', '')[:50]}")

        elif msg_type == "shutdown":
            await self.stop()

    async def _execute_task(self, task: Dict[str, Any]) -> None:
        """Execute a task."""
        task_id = task.get("id", "unknown")
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        self.status = NodeStatus.WORKING
        self._current_task = task
        self._load = min(1.0, self._load + 0.2)

        logger.info(f"Agent {self.agent_id} executing task {task_id}")

        import time
        start_time = time.time()

        result = TaskResult(task_id=task_id, success=False)

        try:
            if task_type in self._task_handlers:
                handler = self._task_handlers[task_type]

                if asyncio.iscoroutinefunction(handler):
                    output = await handler(payload)
                else:
                    output = handler(payload)

                result.success = True
                result.result = output
            else:
                # Default handler
                result.success = True
                result.result = {"status": "completed", "handler": "default"}

            self.stats["tasks_completed"] += 1

        except Exception as e:
            result.success = False
            result.error = str(e)
            self.stats["tasks_failed"] += 1
            logger.error(f"Task {task_id} failed: {e}")

        result.execution_time_ms = (time.time() - start_time) * 1000

        # Report result
        await self._send_to_coordinator({
            "type": "task_result",
            "agent_id": self.agent_id,
            "task_id": task_id,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
        })

        self._task_history.append(result)
        self._current_task = None
        self._load = max(0.0, self._load - 0.2)
        self.status = NodeStatus.IDLE

    async def _heartbeat_sender(self) -> None:
        """Send periodic heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(5.0)

                await self._send_to_coordinator({
                    "type": "heartbeat",
                    "agent_id": self.agent_id,
                    "status": self.status.value,
                    "load": self._load,
                    "tasks_completed": self.stats["tasks_completed"],
                })

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _send_to_coordinator(self, message: Dict[str, Any]) -> None:
        """Send message to coordinator."""
        if self._coordinator_queue:
            await self._coordinator_queue.put(message)
            self.stats["messages_sent"] += 1
        else:
            await self._outbox.put(message)

    async def receive_message(self, message: Dict[str, Any]) -> None:
        """Receive a message from coordinator."""
        await self._inbox.put(message)

    def get_capabilities(self) -> List[str]:
        """Get capability names."""
        return list(self._capabilities.keys())

    def get_proficiency(self, capability: str) -> float:
        """Get proficiency for capability."""
        if capability in self._capabilities:
            return self._capabilities[capability].proficiency
        return 0.0

    def get_load(self) -> float:
        """Get current load."""
        return self._load

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            **self.stats,
            "agent_id": self.agent_id,
            "role": self.role.value,
            "status": self.status.value,
            "load": self._load,
            "capabilities": len(self._capabilities),
        }


def demo():
    """Demonstrate agent node."""
    import asyncio

    print("=" * 60)
    print("BAEL Agent Node Demo")
    print("=" * 60)

    async def run_demo():
        # Create agent
        agent = AgentNode(role=AgentRole.WORKER)

        # Register capabilities
        agent.register_capability("code_review", proficiency=0.9)
        agent.register_capability("testing", proficiency=0.8)
        agent.register_capability("documentation", proficiency=0.7)

        # Register task handlers
        @agent.handler("code_review")
        async def handle_code_review(payload: Dict) -> Dict:
            file = payload.get("file", "unknown")
            await asyncio.sleep(0.1)  # Simulate work
            return {"file": file, "issues": [], "approved": True}

        @agent.handler("write_tests")
        async def handle_tests(payload: Dict) -> Dict:
            module = payload.get("module", "unknown")
            await asyncio.sleep(0.1)
            return {"module": module, "tests_written": 5}

        # Start agent
        await agent.start()

        print(f"\nAgent: {agent.agent_id}")
        print(f"Role: {agent.role.value}")
        print(f"Capabilities: {agent.get_capabilities()}")

        # Simulate receiving tasks
        print("\nProcessing tasks...")

        await agent.receive_message({
            "type": "task",
            "id": "task_001",
            "type": "code_review",
            "payload": {"file": "main.py"},
        })

        await asyncio.sleep(0.5)

        await agent.receive_message({
            "type": "task",
            "id": "task_002",
            "type": "write_tests",
            "payload": {"module": "core"},
        })

        await asyncio.sleep(0.5)

        # Show results
        print(f"\nTask history:")
        for result in agent._task_history:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.task_id}: {result.execution_time_ms:.1f}ms")

        # Stop
        await agent.stop()

        print(f"\nStats: {agent.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
