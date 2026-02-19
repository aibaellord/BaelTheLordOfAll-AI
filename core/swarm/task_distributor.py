"""
BAEL Task Distributor
======================

Intelligent task distribution for swarm agents.
Optimizes work allocation across the swarm.

Features:
- Multiple distribution strategies
- Load balancing
- Affinity routing
- Priority queuing
- Fair scheduling
"""

import asyncio
import hashlib
import heapq
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DistributionStrategy(Enum):
    """Task distribution strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    AFFINITY = "affinity"  # Route to capable agents
    PRIORITY = "priority"  # Priority-based
    CONSISTENT_HASH = "consistent_hash"
    WEIGHTED = "weighted"
    ADAPTIVE = "adaptive"  # Learning-based


class TaskPriority(Enum):
    """Task priorities."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class WorkUnit:
    """A unit of work."""
    id: str
    task_type: str
    payload: Dict[str, Any]

    # Routing
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[str] = field(default_factory=list)
    affinity_agent: Optional[str] = None

    # Constraints
    max_retries: int = 3
    timeout_seconds: float = 300.0

    # State
    retries: int = 0
    assigned_agent: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    def __lt__(self, other: "WorkUnit") -> bool:
        """Compare by priority for heap."""
        return self.priority.value < other.priority.value


@dataclass
class AgentSlot:
    """Agent slot for distribution."""
    agent_id: str
    capabilities: Set[str]

    # State
    current_load: float = 0.0
    max_load: float = 1.0

    # Weighting
    weight: float = 1.0

    # Stats
    tasks_assigned: int = 0
    tasks_completed: int = 0
    avg_execution_time: float = 0.0


class LoadBalancer:
    """Load balancer for agent slots."""

    def __init__(self):
        self._slots: Dict[str, AgentSlot] = {}
        self._round_robin_index = 0
        self._hash_ring: List[Tuple[int, str]] = []

    def add_slot(self, slot: AgentSlot) -> None:
        """Add agent slot."""
        self._slots[slot.agent_id] = slot
        self._rebuild_hash_ring()

    def remove_slot(self, agent_id: str) -> None:
        """Remove agent slot."""
        if agent_id in self._slots:
            del self._slots[agent_id]
            self._rebuild_hash_ring()

    def _rebuild_hash_ring(self) -> None:
        """Rebuild consistent hash ring."""
        self._hash_ring = []

        for agent_id, slot in self._slots.items():
            # Add virtual nodes based on weight
            virtual_nodes = int(slot.weight * 100)
            for i in range(virtual_nodes):
                key = f"{agent_id}:{i}"
                hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
                self._hash_ring.append((hash_val, agent_id))

        self._hash_ring.sort(key=lambda x: x[0])

    def get_by_hash(self, key: str) -> Optional[str]:
        """Get agent by consistent hash."""
        if not self._hash_ring:
            return None

        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)

        for ring_hash, agent_id in self._hash_ring:
            if ring_hash >= hash_val:
                return agent_id

        return self._hash_ring[0][1]

    def get_round_robin(self) -> Optional[str]:
        """Get next agent in round robin."""
        if not self._slots:
            return None

        agents = list(self._slots.keys())
        agent = agents[self._round_robin_index % len(agents)]
        self._round_robin_index += 1

        return agent

    def get_least_loaded(self) -> Optional[str]:
        """Get least loaded agent."""
        if not self._slots:
            return None

        available = [
            (s.current_load / s.max_load, s.agent_id)
            for s in self._slots.values()
            if s.current_load < s.max_load
        ]

        if not available:
            return None

        return min(available, key=lambda x: x[0])[1]

    def get_random(self) -> Optional[str]:
        """Get random agent."""
        if not self._slots:
            return None

        return random.choice(list(self._slots.keys()))

    def get_weighted_random(self) -> Optional[str]:
        """Get weighted random agent."""
        if not self._slots:
            return None

        weights = [s.weight for s in self._slots.values()]
        agents = list(self._slots.keys())

        return random.choices(agents, weights=weights, k=1)[0]

    def update_load(self, agent_id: str, delta: float) -> None:
        """Update agent load."""
        if agent_id in self._slots:
            slot = self._slots[agent_id]
            slot.current_load = max(0.0, min(slot.max_load, slot.current_load + delta))


class TaskDistributor:
    """
    Task distribution system for BAEL swarm.

    Efficiently distributes work across agents.
    """

    def __init__(
        self,
        strategy: DistributionStrategy = DistributionStrategy.ADAPTIVE,
    ):
        self.strategy = strategy

        # Load balancer
        self.load_balancer = LoadBalancer()

        # Priority queue
        self._queue: List[WorkUnit] = []

        # Pending assignments
        self._pending: Dict[str, WorkUnit] = {}

        # Assignment callbacks
        self._on_assign: Optional[Callable] = None

        # Stats
        self.stats = {
            "tasks_distributed": 0,
            "tasks_reassigned": 0,
            "distribution_time_ms": 0.0,
        }

        # Adaptive learning
        self._agent_performance: Dict[str, Dict[str, float]] = {}

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        weight: float = 1.0,
        max_load: float = 1.0,
    ) -> None:
        """Register an agent for task distribution."""
        slot = AgentSlot(
            agent_id=agent_id,
            capabilities=set(capabilities),
            weight=weight,
            max_load=max_load,
        )

        self.load_balancer.add_slot(slot)
        self._agent_performance[agent_id] = {}

        logger.debug(f"Registered agent for distribution: {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        self.load_balancer.remove_slot(agent_id)

        # Reassign pending tasks
        for work_id, work in list(self._pending.items()):
            if work.assigned_agent == agent_id:
                work.assigned_agent = None
                work.retries += 1
                heapq.heappush(self._queue, work)
                del self._pending[work_id]
                self.stats["tasks_reassigned"] += 1

    async def submit(
        self,
        work: WorkUnit,
    ) -> str:
        """
        Submit work for distribution.

        Args:
            work: Work unit to distribute

        Returns:
            Work ID
        """
        heapq.heappush(self._queue, work)
        logger.debug(f"Work submitted: {work.id}")

        return work.id

    async def distribute(self) -> Optional[Tuple[str, WorkUnit]]:
        """
        Distribute next work unit.

        Returns:
            (agent_id, work) or None
        """
        if not self._queue:
            return None

        import time
        start = time.time()

        work = heapq.heappop(self._queue)

        # Find suitable agent
        agent_id = await self._select_agent(work)

        if not agent_id:
            # Re-queue if no agent available
            heapq.heappush(self._queue, work)
            return None

        # Assign
        work.assigned_agent = agent_id
        work.assigned_at = datetime.now()

        self._pending[work.id] = work
        self.load_balancer.update_load(agent_id, 0.2)

        self.stats["tasks_distributed"] += 1
        self.stats["distribution_time_ms"] = (time.time() - start) * 1000

        logger.debug(f"Work {work.id} assigned to {agent_id}")

        if self._on_assign:
            await self._on_assign(agent_id, work)

        return (agent_id, work)

    async def _select_agent(self, work: WorkUnit) -> Optional[str]:
        """Select agent for work based on strategy."""
        # Filter by capabilities
        capable_agents = self._get_capable_agents(work)

        if not capable_agents:
            return None

        # Check affinity
        if work.affinity_agent and work.affinity_agent in capable_agents:
            return work.affinity_agent

        # Apply strategy
        if self.strategy == DistributionStrategy.ROUND_ROBIN:
            return self._select_round_robin(capable_agents)

        elif self.strategy == DistributionStrategy.LEAST_LOADED:
            return self._select_least_loaded(capable_agents)

        elif self.strategy == DistributionStrategy.RANDOM:
            return random.choice(capable_agents) if capable_agents else None

        elif self.strategy == DistributionStrategy.CONSISTENT_HASH:
            return self.load_balancer.get_by_hash(work.id)

        elif self.strategy == DistributionStrategy.WEIGHTED:
            return self._select_weighted(capable_agents)

        elif self.strategy == DistributionStrategy.ADAPTIVE:
            return await self._select_adaptive(work, capable_agents)

        else:
            return self.load_balancer.get_least_loaded()

    def _get_capable_agents(self, work: WorkUnit) -> List[str]:
        """Get agents capable of handling work."""
        required = set(work.required_capabilities)

        if not required:
            return list(self.load_balancer._slots.keys())

        capable = []
        for agent_id, slot in self.load_balancer._slots.items():
            if required.issubset(slot.capabilities):
                capable.append(agent_id)

        return capable

    def _select_round_robin(self, agents: List[str]) -> Optional[str]:
        """Round robin selection."""
        if not agents:
            return None

        agent = self.load_balancer.get_round_robin()
        while agent and agent not in agents:
            agent = self.load_balancer.get_round_robin()

        return agent

    def _select_least_loaded(self, agents: List[str]) -> Optional[str]:
        """Least loaded selection."""
        slots = self.load_balancer._slots

        available = [
            (slots[a].current_load / slots[a].max_load, a)
            for a in agents
            if a in slots and slots[a].current_load < slots[a].max_load
        ]

        if not available:
            return None

        return min(available, key=lambda x: x[0])[1]

    def _select_weighted(self, agents: List[str]) -> Optional[str]:
        """Weighted random selection."""
        slots = self.load_balancer._slots

        weights = [slots[a].weight for a in agents if a in slots]
        valid_agents = [a for a in agents if a in slots]

        if not valid_agents:
            return None

        return random.choices(valid_agents, weights=weights, k=1)[0]

    async def _select_adaptive(
        self,
        work: WorkUnit,
        agents: List[str],
    ) -> Optional[str]:
        """Adaptive selection based on performance."""
        if not agents:
            return None

        scores = []

        for agent_id in agents:
            # Base score from load
            slot = self.load_balancer._slots.get(agent_id)
            if not slot:
                continue

            load_score = 1.0 - (slot.current_load / slot.max_load)

            # Performance score for this task type
            perf = self._agent_performance.get(agent_id, {})
            type_perf = perf.get(work.task_type, 0.5)

            # Combined score
            score = 0.4 * load_score + 0.6 * type_perf
            scores.append((score, agent_id))

        if not scores:
            return None

        return max(scores, key=lambda x: x[0])[1]

    def report_completion(
        self,
        work_id: str,
        success: bool,
        execution_time_ms: float,
    ) -> None:
        """Report work completion."""
        if work_id not in self._pending:
            return

        work = self._pending[work_id]
        agent_id = work.assigned_agent

        if agent_id:
            # Update load
            self.load_balancer.update_load(agent_id, -0.2)

            # Update slot stats
            slot = self.load_balancer._slots.get(agent_id)
            if slot:
                slot.tasks_completed += 1
                # Running average
                slot.avg_execution_time = (
                    slot.avg_execution_time * 0.9 + execution_time_ms * 0.1
                )

            # Update adaptive performance
            if agent_id in self._agent_performance:
                perf = self._agent_performance[agent_id]
                current = perf.get(work.task_type, 0.5)
                # Update based on success
                delta = 0.1 if success else -0.1
                perf[work.task_type] = max(0.1, min(1.0, current + delta))

        del self._pending[work_id]

    def on_assign(self, callback: Callable) -> None:
        """Set assignment callback."""
        self._on_assign = callback

    def get_queue_size(self) -> int:
        """Get pending queue size."""
        return len(self._queue)

    def get_pending_count(self) -> int:
        """Get in-progress count."""
        return len(self._pending)

    def get_stats(self) -> Dict[str, Any]:
        """Get distributor statistics."""
        return {
            **self.stats,
            "queue_size": len(self._queue),
            "pending": len(self._pending),
            "agents": len(self.load_balancer._slots),
            "strategy": self.strategy.value,
        }


def demo():
    """Demonstrate task distributor."""
    import asyncio

    print("=" * 60)
    print("BAEL Task Distributor Demo")
    print("=" * 60)

    async def run_demo():
        distributor = TaskDistributor(strategy=DistributionStrategy.ADAPTIVE)

        # Register agents
        distributor.register_agent("agent_1", ["code", "review"], weight=1.0)
        distributor.register_agent("agent_2", ["code", "testing"], weight=0.8)
        distributor.register_agent("agent_3", ["research", "writing"], weight=1.0)

        print(f"\nRegistered {len(distributor.load_balancer._slots)} agents")

        # Submit work
        work_items = [
            WorkUnit(id="work_1", task_type="code_review", payload={},
                    required_capabilities=["code"], priority=TaskPriority.HIGH),
            WorkUnit(id="work_2", task_type="testing", payload={},
                    required_capabilities=["testing"], priority=TaskPriority.NORMAL),
            WorkUnit(id="work_3", task_type="research", payload={},
                    required_capabilities=["research"], priority=TaskPriority.LOW),
            WorkUnit(id="work_4", task_type="coding", payload={},
                    required_capabilities=["code"], priority=TaskPriority.CRITICAL),
        ]

        print("\nSubmitting work...")
        for work in work_items:
            await distributor.submit(work)

        print(f"Queue size: {distributor.get_queue_size()}")

        # Distribute
        print("\nDistributing...")
        while distributor.get_queue_size() > 0:
            result = await distributor.distribute()
            if result:
                agent_id, work = result
                print(f"  {work.id} ({work.priority.name}) -> {agent_id}")

                # Simulate completion
                await asyncio.sleep(0.1)
                distributor.report_completion(work.id, success=True, execution_time_ms=100)

        print(f"\nStats: {distributor.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
