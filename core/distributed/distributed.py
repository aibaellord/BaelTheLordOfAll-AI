"""
BAEL - Distributed Agent System
Multi-node agent coordination and communication.

Features:
- Distributed task execution
- Agent mesh networking
- Consensus algorithms
- Fault tolerance
- Load balancing
- State synchronization
"""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Distributed")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class NodeStatus(Enum):
    """Distributed node status."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    DRAINING = "draining"
    OFFLINE = "offline"
    FAILED = "failed"


class MessageType(Enum):
    """Types of inter-node messages."""
    HEARTBEAT = "heartbeat"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATE_SYNC = "state_sync"
    VOTE_REQUEST = "vote_request"
    VOTE_RESPONSE = "vote_response"
    LEADER_ANNOUNCE = "leader_announce"
    JOIN = "join"
    LEAVE = "leave"


class ConsensusState(Enum):
    """Consensus algorithm state."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class NodeInfo:
    """Information about a distributed node."""
    id: str
    address: str
    port: int
    status: NodeStatus = NodeStatus.INITIALIZING

    # Capabilities
    capabilities: Set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 10
    current_tasks: int = 0

    # Metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    task_count: int = 0
    error_count: int = 0

    # Timing
    last_heartbeat: datetime = field(default_factory=datetime.now)
    joined_at: datetime = field(default_factory=datetime.now)

    # Consensus
    term: int = 0
    voted_for: Optional[str] = None


@dataclass
class Message:
    """Inter-node message."""
    id: str
    type: MessageType
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: int = 60  # seconds


@dataclass
class DistributedTask:
    """A task distributed across nodes."""
    id: str
    name: str
    payload: Dict[str, Any]

    # Assignment
    assigned_node: Optional[str] = None
    fallback_nodes: List[str] = field(default_factory=list)

    # Execution
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300


# =============================================================================
# MESSAGE BUS
# =============================================================================

class MessageBus:
    """Handles inter-node communication."""

    def __init__(self):
        self._subscribers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self._pending_messages: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self) -> None:
        """Start message processing."""
        self._running = True
        asyncio.create_task(self._process_messages())

    async def stop(self) -> None:
        """Stop message processing."""
        self._running = False

    def subscribe(self, message_type: MessageType, handler: Callable) -> None:
        """Subscribe to a message type."""
        self._subscribers[message_type].append(handler)

    async def publish(self, message: Message) -> None:
        """Publish a message."""
        await self._pending_messages.put(message)

    async def _process_messages(self) -> None:
        """Process pending messages."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._pending_messages.get(),
                    timeout=1.0
                )

                handlers = self._subscribers.get(message.type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")


# =============================================================================
# CONSENSUS (RAFT-INSPIRED)
# =============================================================================

class ConsensusManager:
    """Manages leader election and consensus."""

    def __init__(self, node_id: str, bus: MessageBus):
        self.node_id = node_id
        self.bus = bus
        self.state = ConsensusState.FOLLOWER

        # Raft state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.leader_id: Optional[str] = None

        # Timing
        self.election_timeout = 5.0  # seconds
        self.heartbeat_interval = 1.0  # seconds
        self.last_heartbeat = time.time()

        # Voting
        self.votes_received: Set[str] = set()
        self.known_nodes: Set[str] = set()

        self._running = False

    async def start(self) -> None:
        """Start consensus management."""
        self._running = True

        # Subscribe to messages
        self.bus.subscribe(MessageType.VOTE_REQUEST, self._handle_vote_request)
        self.bus.subscribe(MessageType.VOTE_RESPONSE, self._handle_vote_response)
        self.bus.subscribe(MessageType.LEADER_ANNOUNCE, self._handle_leader_announce)
        self.bus.subscribe(MessageType.HEARTBEAT, self._handle_heartbeat)

        # Start loops
        asyncio.create_task(self._election_loop())
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Stop consensus management."""
        self._running = False

    async def _election_loop(self) -> None:
        """Monitor for election timeout."""
        while self._running:
            await asyncio.sleep(0.5)

            if self.state == ConsensusState.LEADER:
                continue

            elapsed = time.time() - self.last_heartbeat

            # Add randomness to prevent split votes
            timeout = self.election_timeout + secrets.randbelow(3)

            if elapsed > timeout:
                await self._start_election()

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats if leader."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)

            if self.state == ConsensusState.LEADER:
                await self._send_heartbeat()

    async def _start_election(self) -> None:
        """Start a new election."""
        logger.info(f"Node {self.node_id}: Starting election for term {self.current_term + 1}")

        self.state = ConsensusState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}

        # Request votes from all nodes
        message = Message(
            id=secrets.token_hex(8),
            type=MessageType.VOTE_REQUEST,
            sender_id=self.node_id,
            recipient_id=None,  # Broadcast
            payload={
                "term": self.current_term,
                "candidate_id": self.node_id
            }
        )

        await self.bus.publish(message)

        # Check if we won (single node cluster)
        self._check_election_result()

    async def _handle_vote_request(self, message: Message) -> None:
        """Handle vote request."""
        term = message.payload.get("term", 0)
        candidate_id = message.payload.get("candidate_id")

        # Update term if needed
        if term > self.current_term:
            self.current_term = term
            self.state = ConsensusState.FOLLOWER
            self.voted_for = None

        # Decide whether to vote
        vote_granted = False

        if term >= self.current_term and (self.voted_for is None or self.voted_for == candidate_id):
            vote_granted = True
            self.voted_for = candidate_id
            self.last_heartbeat = time.time()

        # Send vote response
        response = Message(
            id=secrets.token_hex(8),
            type=MessageType.VOTE_RESPONSE,
            sender_id=self.node_id,
            recipient_id=candidate_id,
            payload={
                "term": self.current_term,
                "vote_granted": vote_granted
            }
        )

        await self.bus.publish(response)

    async def _handle_vote_response(self, message: Message) -> None:
        """Handle vote response."""
        if message.recipient_id != self.node_id:
            return

        if self.state != ConsensusState.CANDIDATE:
            return

        term = message.payload.get("term", 0)
        vote_granted = message.payload.get("vote_granted", False)

        if term > self.current_term:
            self.current_term = term
            self.state = ConsensusState.FOLLOWER
            return

        if vote_granted:
            self.votes_received.add(message.sender_id)
            self._check_election_result()

    def _check_election_result(self) -> None:
        """Check if we've won the election."""
        if self.state != ConsensusState.CANDIDATE:
            return

        # Need majority of known nodes
        needed = (len(self.known_nodes) + 1) // 2 + 1

        if len(self.votes_received) >= needed or len(self.known_nodes) == 0:
            self._become_leader()

    def _become_leader(self) -> None:
        """Become the cluster leader."""
        logger.info(f"Node {self.node_id}: Became leader for term {self.current_term}")

        self.state = ConsensusState.LEADER
        self.leader_id = self.node_id

        # Announce leadership
        asyncio.create_task(self._announce_leadership())

    async def _announce_leadership(self) -> None:
        """Announce leadership to cluster."""
        message = Message(
            id=secrets.token_hex(8),
            type=MessageType.LEADER_ANNOUNCE,
            sender_id=self.node_id,
            recipient_id=None,
            payload={
                "term": self.current_term,
                "leader_id": self.node_id
            }
        )

        await self.bus.publish(message)

    async def _handle_leader_announce(self, message: Message) -> None:
        """Handle leader announcement."""
        term = message.payload.get("term", 0)
        leader_id = message.payload.get("leader_id")

        if term >= self.current_term:
            self.current_term = term
            self.leader_id = leader_id
            self.state = ConsensusState.FOLLOWER
            self.last_heartbeat = time.time()

    async def _send_heartbeat(self) -> None:
        """Send heartbeat to followers."""
        message = Message(
            id=secrets.token_hex(8),
            type=MessageType.HEARTBEAT,
            sender_id=self.node_id,
            recipient_id=None,
            payload={
                "term": self.current_term,
                "leader_id": self.node_id
            }
        )

        await self.bus.publish(message)

    async def _handle_heartbeat(self, message: Message) -> None:
        """Handle heartbeat from leader."""
        term = message.payload.get("term", 0)
        leader_id = message.payload.get("leader_id")

        if term >= self.current_term:
            self.current_term = term
            self.leader_id = leader_id
            self.state = ConsensusState.FOLLOWER
            self.last_heartbeat = time.time()

    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self.state == ConsensusState.LEADER


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Distributes tasks across nodes."""

    def __init__(self):
        self._nodes: Dict[str, NodeInfo] = {}
        self._strategy = "least_connections"

    def register_node(self, node: NodeInfo) -> None:
        """Register a node."""
        self._nodes[node.id] = node

    def unregister_node(self, node_id: str) -> None:
        """Unregister a node."""
        self._nodes.pop(node_id, None)

    def update_node(self, node_id: str, **kwargs) -> None:
        """Update node info."""
        if node_id in self._nodes:
            for key, value in kwargs.items():
                if hasattr(self._nodes[node_id], key):
                    setattr(self._nodes[node_id], key, value)

    def select_node(
        self,
        required_capability: str = None,
        exclude_nodes: Set[str] = None
    ) -> Optional[NodeInfo]:
        """Select best node for task."""
        candidates = [
            n for n in self._nodes.values()
            if n.status == NodeStatus.ACTIVE
            and n.current_tasks < n.max_concurrent_tasks
            and (n.id not in (exclude_nodes or set()))
            and (required_capability is None or required_capability in n.capabilities)
        ]

        if not candidates:
            return None

        if self._strategy == "least_connections":
            return min(candidates, key=lambda n: n.current_tasks)

        elif self._strategy == "round_robin":
            # Simple implementation - could use counter
            return candidates[0]

        elif self._strategy == "weighted":
            # Weight by available capacity
            return max(candidates, key=lambda n: n.max_concurrent_tasks - n.current_tasks)

        elif self._strategy == "resource_based":
            # Consider CPU and memory
            return min(
                candidates,
                key=lambda n: n.cpu_usage * 0.5 + n.memory_usage * 0.5
            )

        return candidates[0]

    def get_healthy_nodes(self) -> List[NodeInfo]:
        """Get all healthy nodes."""
        return [
            n for n in self._nodes.values()
            if n.status in [NodeStatus.ACTIVE, NodeStatus.BUSY]
        ]


# =============================================================================
# DISTRIBUTED COORDINATOR
# =============================================================================

class DistributedCoordinator:
    """Coordinates distributed agent operations."""

    def __init__(self, node_id: str = None, address: str = "localhost", port: int = 8000):
        self.node_id = node_id or secrets.token_hex(8)

        # This node's info
        self.node_info = NodeInfo(
            id=self.node_id,
            address=address,
            port=port,
            status=NodeStatus.INITIALIZING,
            capabilities={"general", "thinking", "coding"}
        )

        # Components
        self.bus = MessageBus()
        self.consensus = ConsensusManager(self.node_id, self.bus)
        self.load_balancer = LoadBalancer()

        # Tasks
        self._tasks: Dict[str, DistributedTask] = {}
        self._task_handlers: Dict[str, Callable] = {}

        # State
        self._running = False

    async def start(self) -> None:
        """Start the distributed coordinator."""
        logger.info(f"Starting distributed node: {self.node_id}")

        await self.bus.start()
        await self.consensus.start()

        # Register this node
        self.load_balancer.register_node(self.node_info)

        # Subscribe to task messages
        self.bus.subscribe(MessageType.TASK_REQUEST, self._handle_task_request)
        self.bus.subscribe(MessageType.TASK_RESPONSE, self._handle_task_response)
        self.bus.subscribe(MessageType.JOIN, self._handle_join)
        self.bus.subscribe(MessageType.LEAVE, self._handle_leave)

        self.node_info.status = NodeStatus.ACTIVE
        self._running = True

        # Start monitoring
        asyncio.create_task(self._health_check_loop())

        logger.info(f"Node {self.node_id} started")

    async def stop(self) -> None:
        """Stop the coordinator."""
        self._running = False

        # Announce departure
        message = Message(
            id=secrets.token_hex(8),
            type=MessageType.LEAVE,
            sender_id=self.node_id,
            recipient_id=None,
            payload={"node_id": self.node_id}
        )
        await self.bus.publish(message)

        await self.consensus.stop()
        await self.bus.stop()

        self.node_info.status = NodeStatus.OFFLINE

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a task handler."""
        self._task_handlers[task_type] = handler

    async def submit_task(self, task: DistributedTask) -> str:
        """Submit a task for distributed execution."""
        self._tasks[task.id] = task

        # Select node
        node = self.load_balancer.select_node()

        if not node:
            task.status = "failed"
            task.error = "No available nodes"
            return task.id

        task.assigned_node = node.id
        task.status = "assigned"

        # Send task request
        message = Message(
            id=secrets.token_hex(8),
            type=MessageType.TASK_REQUEST,
            sender_id=self.node_id,
            recipient_id=node.id,
            payload={
                "task_id": task.id,
                "task_name": task.name,
                "payload": task.payload
            }
        )

        await self.bus.publish(message)

        return task.id

    async def _handle_task_request(self, message: Message) -> None:
        """Handle incoming task request."""
        if message.recipient_id != self.node_id:
            return

        task_id = message.payload.get("task_id")
        task_name = message.payload.get("task_name")
        payload = message.payload.get("payload", {})

        logger.info(f"Received task: {task_name}")

        self.node_info.current_tasks += 1

        try:
            # Find handler
            handler = self._task_handlers.get(task_name)

            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(payload)
                else:
                    result = handler(payload)
            else:
                result = {"status": "no_handler", "task": task_name}

            # Send response
            response = Message(
                id=secrets.token_hex(8),
                type=MessageType.TASK_RESPONSE,
                sender_id=self.node_id,
                recipient_id=message.sender_id,
                payload={
                    "task_id": task_id,
                    "status": "completed",
                    "result": result
                }
            )

        except Exception as e:
            response = Message(
                id=secrets.token_hex(8),
                type=MessageType.TASK_RESPONSE,
                sender_id=self.node_id,
                recipient_id=message.sender_id,
                payload={
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e)
                }
            )

        finally:
            self.node_info.current_tasks -= 1

        await self.bus.publish(response)

    async def _handle_task_response(self, message: Message) -> None:
        """Handle task response."""
        if message.recipient_id != self.node_id:
            return

        task_id = message.payload.get("task_id")

        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = message.payload.get("status", "unknown")
            task.result = message.payload.get("result")
            task.error = message.payload.get("error")
            task.completed_at = datetime.now()

    async def _handle_join(self, message: Message) -> None:
        """Handle node join."""
        node_data = message.payload.get("node_info", {})

        node = NodeInfo(
            id=node_data.get("id", message.sender_id),
            address=node_data.get("address", "unknown"),
            port=node_data.get("port", 8000),
            capabilities=set(node_data.get("capabilities", []))
        )

        self.load_balancer.register_node(node)
        self.consensus.known_nodes.add(node.id)

        logger.info(f"Node joined: {node.id}")

    async def _handle_leave(self, message: Message) -> None:
        """Handle node leave."""
        node_id = message.payload.get("node_id", message.sender_id)

        self.load_balancer.unregister_node(node_id)
        self.consensus.known_nodes.discard(node_id)

        logger.info(f"Node left: {node_id}")

    async def _health_check_loop(self) -> None:
        """Periodic health check."""
        while self._running:
            await asyncio.sleep(5)

            # Check for stale nodes
            now = datetime.now()
            stale_timeout = timedelta(seconds=30)

            for node in self.load_balancer.get_healthy_nodes():
                if now - node.last_heartbeat > stale_timeout:
                    node.status = NodeStatus.FAILED
                    logger.warning(f"Node {node.id} appears to have failed")

    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status."""
        return {
            "node_id": self.node_id,
            "status": self.node_info.status.value,
            "is_leader": self.consensus.is_leader(),
            "leader_id": self.consensus.leader_id,
            "term": self.consensus.current_term,
            "known_nodes": len(self.consensus.known_nodes),
            "healthy_nodes": len(self.load_balancer.get_healthy_nodes()),
            "pending_tasks": sum(1 for t in self._tasks.values() if t.status == "pending")
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test distributed system."""
    # Create two nodes
    node1 = DistributedCoordinator(node_id="node-1", port=8001)
    node2 = DistributedCoordinator(node_id="node-2", port=8002)

    # Register handlers
    async def think_handler(payload: Dict) -> Dict:
        prompt = payload.get("prompt", "")
        await asyncio.sleep(0.1)  # Simulate work
        return {"response": f"Thought about: {prompt[:30]}..."}

    node1.register_handler("think", think_handler)
    node2.register_handler("think", think_handler)

    # Start nodes
    await node1.start()
    await node2.start()

    # Manually connect nodes (in real system, would use discovery)
    node1.load_balancer.register_node(node2.node_info)
    node1.consensus.known_nodes.add(node2.node_id)
    node2.load_balancer.register_node(node1.node_info)
    node2.consensus.known_nodes.add(node1.node_id)

    # Wait for leader election
    await asyncio.sleep(3)

    print(f"Node 1 status: {node1.get_status()}")
    print(f"Node 2 status: {node2.get_status()}")

    # Submit task
    task = DistributedTask(
        id="task-1",
        name="think",
        payload={"prompt": "What is the meaning of life?"}
    )

    await node1.submit_task(task)

    # Wait for completion
    await asyncio.sleep(2)

    print(f"\nTask status: {task.status}")
    print(f"Task result: {task.result}")

    # Cleanup
    await node1.stop()
    await node2.stop()


if __name__ == "__main__":
    asyncio.run(main())
