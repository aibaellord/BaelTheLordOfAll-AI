"""
BAEL Distributed Coordination System - Multi-node cluster management with consensus

Features:
- Redis-based distributed coordination
- Leader election and consensus
- Node discovery and health monitoring
- Cross-instance agent coordination
- Automatic failover and recovery
- Distributed task scheduling
- State synchronization
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class NodeRole(str, Enum):
    """Node role in the cluster"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


class NodeStatus(str, Enum):
    """Node health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class NodeInfo:
    """Information about a cluster node"""
    node_id: str
    hostname: str
    port: int
    role: NodeRole = NodeRole.FOLLOWER
    status: NodeStatus = NodeStatus.HEALTHY
    last_heartbeat: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    load: float = 0.0  # CPU load 0-100
    agents_count: int = 0
    tasks_count: int = 0

    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'hostname': self.hostname,
            'port': self.port,
            'role': self.role.value,
            'status': self.status.value,
            'last_heartbeat': self.last_heartbeat,
            'capabilities': self.capabilities,
            'load': self.load,
            'agents_count': self.agents_count,
            'tasks_count': self.tasks_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'NodeInfo':
        return cls(
            node_id=data['node_id'],
            hostname=data['hostname'],
            port=data['port'],
            role=NodeRole(data['role']),
            status=NodeStatus(data['status']),
            last_heartbeat=data.get('last_heartbeat', ''),
            capabilities=data.get('capabilities', {}),
            load=data.get('load', 0.0),
            agents_count=data.get('agents_count', 0),
            tasks_count=data.get('tasks_count', 0),
        )


@dataclass
class DistributedLock:
    """Distributed lock for coordination"""
    lock_id: str
    owner_node_id: str
    acquired_at: str
    expires_at: str
    resource: str


class ConsensusEngine:
    """Raft-inspired consensus for leader election"""

    def __init__(self, node_id: str, redis_client):
        self.node_id = node_id
        self.redis = redis_client
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.election_timeout = 5  # seconds

    async def request_vote(self, term: int, candidate_id: str) -> bool:
        """Vote for a candidate in an election"""
        if term > self.current_term:
            self.current_term = term
            self.voted_for = candidate_id

            # Store vote in Redis
            await self.redis.setex(
                f"vote:{self.node_id}:{term}",
                self.election_timeout,
                candidate_id
            )

            logger.info(f"Node {self.node_id} voted for {candidate_id} in term {term}")
            return True

        return False

    async def start_election(self) -> bool:
        """Start a new election"""
        self.current_term += 1
        self.voted_for = self.node_id

        logger.info(f"Node {self.node_id} starting election for term {self.current_term}")

        # Get all nodes
        nodes = await self._get_cluster_nodes()
        votes = 1  # Vote for self

        # Request votes from other nodes
        for node_id in nodes:
            if node_id != self.node_id:
                vote_key = f"vote_request:{node_id}:{self.current_term}"
                await self.redis.setex(
                    vote_key,
                    self.election_timeout,
                    json.dumps({
                        'candidate_id': self.node_id,
                        'term': self.current_term,
                    })
                )

        # Wait for votes
        await asyncio.sleep(2)

        # Count votes
        for node_id in nodes:
            vote_key = f"vote:{node_id}:{self.current_term}"
            vote = await self.redis.get(vote_key)
            if vote and vote.decode() == self.node_id:
                votes += 1

        # Majority wins
        quorum = (len(nodes) + 1) // 2 + 1
        won = votes >= quorum

        if won:
            logger.info(f"Node {self.node_id} won election with {votes}/{len(nodes)} votes")

        return won

    async def _get_cluster_nodes(self) -> List[str]:
        """Get all cluster node IDs"""
        keys = await self.redis.keys("node:*")
        return [key.decode().split(':')[1] for key in keys]


class ClusterManager:
    """Manages distributed cluster coordination"""

    def __init__(
        self,
        node_id: str,
        hostname: str,
        port: int,
        redis_url: str = "redis://localhost:6379"
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package required for distributed coordination")

        self.node_id = node_id
        self.node_info = NodeInfo(
            node_id=node_id,
            hostname=hostname,
            port=port,
        )

        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.consensus: Optional[ConsensusEngine] = None

        self.heartbeat_interval = 3  # seconds
        self.heartbeat_timeout = 10  # seconds
        self.running = False

        self.locks: Dict[str, DistributedLock] = {}

    async def start(self):
        """Start cluster coordination"""
        self.redis = await redis.from_url(self.redis_url, decode_responses=False)
        self.consensus = ConsensusEngine(self.node_id, self.redis)
        self.running = True

        # Register node
        await self._register_node()

        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._monitor_cluster())
        asyncio.create_task(self._leader_election_loop())

        logger.info(f"Cluster manager started for node {self.node_id}")

    async def stop(self):
        """Stop cluster coordination"""
        self.running = False

        # Unregister node
        await self._unregister_node()

        if self.redis:
            await self.redis.close()

        logger.info(f"Cluster manager stopped for node {self.node_id}")

    async def _register_node(self):
        """Register this node in the cluster"""
        self.node_info.last_heartbeat = datetime.utcnow().isoformat()

        await self.redis.setex(
            f"node:{self.node_id}",
            self.heartbeat_timeout,
            json.dumps(self.node_info.to_dict())
        )

        logger.info(f"Node {self.node_id} registered")

    async def _unregister_node(self):
        """Unregister this node from the cluster"""
        await self.redis.delete(f"node:{self.node_id}")
        logger.info(f"Node {self.node_id} unregistered")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                self.node_info.last_heartbeat = datetime.utcnow().isoformat()

                await self.redis.setex(
                    f"node:{self.node_id}",
                    self.heartbeat_timeout,
                    json.dumps(self.node_info.to_dict())
                )

                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _monitor_cluster(self):
        """Monitor cluster health"""
        while self.running:
            try:
                nodes = await self.get_cluster_nodes()

                # Check for dead nodes
                now = datetime.utcnow()
                for node in nodes:
                    if node.last_heartbeat:
                        last_hb = datetime.fromisoformat(node.last_heartbeat)
                        if (now - last_hb).seconds > self.heartbeat_timeout:
                            node.status = NodeStatus.OFFLINE
                            logger.warning(f"Node {node.node_id} appears offline")

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Cluster monitoring error: {e}")
                await asyncio.sleep(5)

    async def _leader_election_loop(self):
        """Perform leader elections"""
        await asyncio.sleep(2)  # Initial delay

        while self.running:
            try:
                # Check if we have a leader
                leader = await self.get_leader()

                if not leader:
                    # No leader, start election
                    won = await self.consensus.start_election()
                    if won:
                        self.node_info.role = NodeRole.LEADER
                        await self._register_node()
                        logger.info(f"Node {self.node_id} became leader")

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Leader election error: {e}")
                await asyncio.sleep(5)

    async def get_cluster_nodes(self) -> List[NodeInfo]:
        """Get all nodes in the cluster"""
        keys = await self.redis.keys("node:*")
        nodes = []

        for key in keys:
            data = await self.redis.get(key)
            if data:
                node = NodeInfo.from_dict(json.loads(data))
                nodes.append(node)

        return nodes

    async def get_leader(self) -> Optional[NodeInfo]:
        """Get current cluster leader"""
        nodes = await self.get_cluster_nodes()

        for node in nodes:
            if node.role == NodeRole.LEADER:
                return node

        return None

    async def acquire_lock(
        self,
        resource: str,
        ttl_seconds: int = 30
    ) -> Optional[str]:
        """Acquire distributed lock"""
        lock_key = f"lock:{resource}"
        lock_id = str(uuid.uuid4())

        # Try to acquire lock
        acquired = await self.redis.set(
            lock_key,
            json.dumps({
                'lock_id': lock_id,
                'owner': self.node_id,
                'acquired_at': datetime.utcnow().isoformat(),
            }),
            nx=True,
            ex=ttl_seconds
        )

        if acquired:
            logger.info(f"Node {self.node_id} acquired lock on {resource}")
            return lock_id

        return None

    async def release_lock(self, resource: str, lock_id: str) -> bool:
        """Release distributed lock"""
        lock_key = f"lock:{resource}"

        # Check ownership
        data = await self.redis.get(lock_key)
        if data:
            lock_info = json.loads(data)
            if lock_info['lock_id'] == lock_id:
                await self.redis.delete(lock_key)
                logger.info(f"Node {self.node_id} released lock on {resource}")
                return True

        return False

    async def route_to_best_node(
        self,
        task_requirements: Dict[str, Any]
    ) -> Optional[NodeInfo]:
        """Route task to best available node"""
        nodes = await self.get_cluster_nodes()

        # Filter healthy nodes
        healthy_nodes = [
            n for n in nodes
            if n.status == NodeStatus.HEALTHY
        ]

        if not healthy_nodes:
            return None

        # Sort by load (ascending)
        healthy_nodes.sort(key=lambda n: n.load)

        # Return least loaded node
        return healthy_nodes[0]

    async def sync_state(self, state_key: str, state_data: Dict) -> bool:
        """Synchronize state across cluster"""
        state_key_full = f"state:{state_key}"

        await self.redis.setex(
            state_key_full,
            300,  # 5 minutes
            json.dumps(state_data)
        )

        return True

    async def get_state(self, state_key: str) -> Optional[Dict]:
        """Get synchronized state"""
        state_key_full = f"state:{state_key}"

        data = await self.redis.get(state_key_full)
        if data:
            return json.loads(data)

        return None

    async def publish_event(self, channel: str, event_data: Dict):
        """Publish event to all cluster nodes"""
        await self.redis.publish(
            f"cluster:{channel}",
            json.dumps(event_data)
        )

    async def subscribe_events(self, channel: str, handler: callable):
        """Subscribe to cluster events"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"cluster:{channel}")

        async for message in pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                await handler(event_data)

    async def get_cluster_stats(self) -> Dict:
        """Get cluster-wide statistics"""
        nodes = await self.get_cluster_nodes()

        total_agents = sum(n.agents_count for n in nodes)
        total_tasks = sum(n.tasks_count for n in nodes)
        avg_load = sum(n.load for n in nodes) / len(nodes) if nodes else 0

        return {
            'total_nodes': len(nodes),
            'healthy_nodes': len([n for n in nodes if n.status == NodeStatus.HEALTHY]),
            'leader_node': (await self.get_leader()).node_id if await self.get_leader() else None,
            'total_agents': total_agents,
            'total_tasks': total_tasks,
            'average_load': round(avg_load, 2),
        }
