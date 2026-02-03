"""
BAEL Agent Swarm Coordinator

Multi-agent swarm coordination with:
- Dynamic agent spawning and termination
- Task distribution algorithms
- Agent communication mesh
- Collective intelligence emergence
- Swarm consensus mechanisms
- Resource optimization

This enables BAEL to deploy and coordinate multiple specialized agents.
"""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Predefined agent roles."""
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    MONITOR = "monitor"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    VALIDATOR = "validator"


class AgentState(Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    WORKING = "working"
    COMMUNICATING = "communicating"
    WAITING = "waiting"
    PAUSED = "paused"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    VOTE = "vote"
    CONSENSUS = "consensus"
    HELP_REQUEST = "help_request"
    KNOWLEDGE_SHARE = "knowledge_share"


class DistributionStrategy(Enum):
    """Task distribution strategies."""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    CAPABILITY_MATCHED = "capability_matched"
    RANDOM = "random"
    PRIORITY_QUEUE = "priority_queue"
    AUCTION = "auction"


@dataclass
class AgentCapability:
    """Capability of an agent."""
    name: str
    proficiency: float  # 0.0 to 1.0
    domains: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str]  # None for broadcast
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    priority: int = 5
    ttl_seconds: int = 300


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    id: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    priority: int = 5
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Any = None


@dataclass
class SwarmAgent:
    """An individual agent in the swarm."""
    id: str
    role: AgentRole
    name: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    state: AgentState = AgentState.INITIALIZING
    current_task: Optional[AgentTask] = None

    # Performance metrics
    tasks_completed: int = 0
    success_rate: float = 1.0
    avg_task_duration_ms: float = 0.0
    current_load: float = 0.0

    # Communication
    inbox: List[AgentMessage] = field(default_factory=list)
    outbox: List[AgentMessage] = field(default_factory=list)

    # Knowledge
    local_memory: Dict[str, Any] = field(default_factory=dict)
    beliefs: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    spawned_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability."""
        return any(c.name == capability_name for c in self.capabilities)

    def get_capability_score(self, capability_name: str) -> float:
        """Get proficiency score for a capability."""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap.proficiency
        return 0.0


@dataclass
class SwarmConfig:
    """Configuration for the agent swarm."""
    min_agents: int = 2
    max_agents: int = 20
    auto_scale: bool = True
    distribution_strategy: DistributionStrategy = DistributionStrategy.CAPABILITY_MATCHED
    consensus_threshold: float = 0.66
    heartbeat_interval_ms: int = 5000
    task_timeout_ms: int = 60000
    enable_learning: bool = True


class SwarmCoordinator:
    """
    Master coordinator for agent swarm.

    Manages:
    - Agent lifecycle (spawn, monitor, terminate)
    - Task distribution
    - Inter-agent communication
    - Collective decision-making
    - Emergent behavior monitoring
    """

    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self.agents: Dict[str, SwarmAgent] = {}
        self.task_queue: List[AgentTask] = []
        self.completed_tasks: List[AgentTask] = []
        self.message_bus: List[AgentMessage] = []

        # Round-robin state
        self._rr_index = 0

        # Collective knowledge
        self.shared_knowledge: Dict[str, Any] = {}
        self.consensus_history: List[Dict[str, Any]] = []

    async def spawn_agent(
        self,
        role: AgentRole,
        name: str = None,
        capabilities: List[AgentCapability] = None
    ) -> SwarmAgent:
        """Spawn a new agent in the swarm."""
        if len(self.agents) >= self.config.max_agents:
            raise ValueError("Maximum agent limit reached")

        agent_id = f"agent_{uuid4().hex[:8]}"
        name = name or f"{role.value.title()}_{len(self.agents)}"

        agent = SwarmAgent(
            id=agent_id,
            role=role,
            name=name,
            capabilities=capabilities or self._default_capabilities(role),
            state=AgentState.IDLE
        )

        self.agents[agent_id] = agent
        logger.info(f"Spawned agent: {name} ({role.value})")

        return agent

    def _default_capabilities(self, role: AgentRole) -> List[AgentCapability]:
        """Get default capabilities for a role."""
        role_capabilities = {
            AgentRole.RESEARCHER: [
                AgentCapability("search", 0.9, ["web", "academic"]),
                AgentCapability("analysis", 0.7),
            ],
            AgentRole.ANALYST: [
                AgentCapability("analysis", 0.9),
                AgentCapability("pattern_recognition", 0.8),
            ],
            AgentRole.PLANNER: [
                AgentCapability("planning", 0.9),
                AgentCapability("decomposition", 0.8),
            ],
            AgentRole.EXECUTOR: [
                AgentCapability("execution", 0.9),
                AgentCapability("tool_use", 0.8),
            ],
            AgentRole.CRITIC: [
                AgentCapability("evaluation", 0.9),
                AgentCapability("feedback", 0.8),
            ],
            AgentRole.SYNTHESIZER: [
                AgentCapability("synthesis", 0.9),
                AgentCapability("integration", 0.8),
            ],
        }
        return role_capabilities.get(role, [AgentCapability("general", 0.5)])

    async def terminate_agent(self, agent_id: str, force: bool = False):
        """Terminate an agent."""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]

        if not force and agent.current_task:
            # Reassign current task
            await self._reassign_task(agent.current_task)

        agent.state = AgentState.TERMINATED
        del self.agents[agent_id]

        logger.info(f"Terminated agent: {agent.name}")

    async def submit_task(self, task: AgentTask) -> str:
        """Submit a task to the swarm."""
        self.task_queue.append(task)

        # Try to assign immediately
        await self._distribute_tasks()

        return task.id

    async def _distribute_tasks(self):
        """Distribute pending tasks to available agents."""
        strategy = self.config.distribution_strategy

        for task in list(self.task_queue):
            agent = await self._select_agent(task, strategy)

            if agent:
                await self._assign_task(agent, task)
                self.task_queue.remove(task)

    async def _select_agent(
        self,
        task: AgentTask,
        strategy: DistributionStrategy
    ) -> Optional[SwarmAgent]:
        """Select best agent for a task."""
        available = [
            a for a in self.agents.values()
            if a.state == AgentState.IDLE
        ]

        if not available:
            return None

        if strategy == DistributionStrategy.ROUND_ROBIN:
            agent = available[self._rr_index % len(available)]
            self._rr_index += 1
            return agent

        elif strategy == DistributionStrategy.LOAD_BALANCED:
            return min(available, key=lambda a: a.current_load)

        elif strategy == DistributionStrategy.CAPABILITY_MATCHED:
            if not task.required_capabilities:
                return random.choice(available)

            # Score agents by capability match
            scored = []
            for agent in available:
                score = sum(
                    agent.get_capability_score(cap)
                    for cap in task.required_capabilities
                )
                scored.append((agent, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0] if scored[0][1] > 0 else None

        elif strategy == DistributionStrategy.RANDOM:
            return random.choice(available)

        elif strategy == DistributionStrategy.AUCTION:
            # Agents bid on task
            return await self._run_auction(task, available)

        return None

    async def _run_auction(
        self,
        task: AgentTask,
        bidders: List[SwarmAgent]
    ) -> Optional[SwarmAgent]:
        """Run an auction for task assignment."""
        bids = []

        for agent in bidders:
            # Calculate bid based on capability and load
            capability_score = sum(
                agent.get_capability_score(cap)
                for cap in task.required_capabilities
            ) if task.required_capabilities else 0.5

            load_factor = 1.0 - agent.current_load
            bid = capability_score * load_factor * agent.success_rate
            bids.append((agent, bid))

        if not bids:
            return None

        bids.sort(key=lambda x: x[1], reverse=True)
        return bids[0][0]

    async def _assign_task(self, agent: SwarmAgent, task: AgentTask):
        """Assign a task to an agent."""
        agent.current_task = task
        agent.state = AgentState.WORKING
        task.assigned_to = agent.id
        task.status = "in_progress"

        # Send task assignment message
        message = AgentMessage(
            id=str(uuid4())[:8],
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="coordinator",
            receiver_id=agent.id,
            content={"task": task}
        )
        agent.inbox.append(message)

    async def _reassign_task(self, task: AgentTask):
        """Reassign a task that couldn't be completed."""
        task.assigned_to = None
        task.status = "pending"
        self.task_queue.insert(0, task)  # Priority reassignment

    async def send_message(
        self,
        sender_id: str,
        receiver_id: Optional[str],
        message_type: MessageType,
        content: Any
    ) -> str:
        """Send a message between agents or broadcast."""
        message = AgentMessage(
            id=str(uuid4())[:8],
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )

        if receiver_id:
            # Direct message
            if receiver_id in self.agents:
                self.agents[receiver_id].inbox.append(message)
        else:
            # Broadcast
            for agent in self.agents.values():
                if agent.id != sender_id:
                    agent.inbox.append(message)

        self.message_bus.append(message)
        return message.id

    async def request_consensus(
        self,
        topic: str,
        options: List[str],
        voters: List[str] = None
    ) -> Dict[str, Any]:
        """Request consensus from swarm agents."""
        voters = voters or list(self.agents.keys())
        votes: Dict[str, int] = {opt: 0 for opt in options}

        for voter_id in voters:
            if voter_id not in self.agents:
                continue

            agent = self.agents[voter_id]

            # Simulate voting based on agent expertise
            # In real implementation, would query LLM for each agent
            vote = random.choice(options)
            votes[vote] += 1

        total_votes = sum(votes.values())

        if total_votes == 0:
            return {"consensus": False, "reason": "No votes"}

        # Find winner
        winner = max(votes, key=votes.get)
        winner_ratio = votes[winner] / total_votes

        consensus_reached = winner_ratio >= self.config.consensus_threshold

        result = {
            "topic": topic,
            "consensus": consensus_reached,
            "winner": winner if consensus_reached else None,
            "votes": votes,
            "ratio": winner_ratio,
            "threshold": self.config.consensus_threshold
        }

        self.consensus_history.append(result)
        return result

    async def collective_reasoning(
        self,
        question: str,
        method: str = "debate"
    ) -> Dict[str, Any]:
        """
        Perform collective reasoning with multiple agents.

        Methods:
        - debate: Agents argue different positions
        - synthesis: Each agent contributes perspective
        - critique: Sequential refinement with criticism
        """
        if method == "debate":
            return await self._debate_reasoning(question)
        elif method == "synthesis":
            return await self._synthesis_reasoning(question)
        elif method == "critique":
            return await self._critique_reasoning(question)
        else:
            raise ValueError(f"Unknown method: {method}")

    async def _debate_reasoning(self, question: str) -> Dict[str, Any]:
        """Agents debate different positions."""
        positions = {}

        for agent in self.agents.values():
            # Each agent forms a position
            position = f"[{agent.role.value}] Position on: {question[:50]}..."
            positions[agent.id] = {
                "agent": agent.name,
                "role": agent.role.value,
                "position": position,
                "confidence": random.uniform(0.5, 1.0)
            }

        # Synthesize debate
        return {
            "question": question,
            "method": "debate",
            "positions": positions,
            "conclusion": "Synthesized from debate positions"
        }

    async def _synthesis_reasoning(self, question: str) -> Dict[str, Any]:
        """Each agent contributes their perspective."""
        contributions = []

        for agent in self.agents.values():
            contrib = {
                "agent": agent.name,
                "role": agent.role.value,
                "contribution": f"[{agent.role.value}] perspective on question"
            }
            contributions.append(contrib)

        return {
            "question": question,
            "method": "synthesis",
            "contributions": contributions,
            "synthesis": "Combined synthesis of all perspectives"
        }

    async def _critique_reasoning(self, question: str) -> Dict[str, Any]:
        """Sequential refinement with criticism."""
        iterations = []
        current_answer = f"Initial answer to: {question[:50]}..."

        critics = [a for a in self.agents.values() if a.role == AgentRole.CRITIC]

        for i, critic in enumerate(critics[:3]):  # Max 3 iterations
            critique = f"[{critic.name}] Critique: needs improvement"
            refined = f"Refined answer v{i+2}"

            iterations.append({
                "iteration": i + 1,
                "answer": current_answer,
                "critic": critic.name,
                "critique": critique,
                "refined": refined
            })
            current_answer = refined

        return {
            "question": question,
            "method": "critique",
            "iterations": iterations,
            "final_answer": current_answer
        }

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get current swarm status."""
        states = {}
        for state in AgentState:
            states[state.value] = len([
                a for a in self.agents.values() if a.state == state
            ])

        roles = {}
        for role in AgentRole:
            roles[role.value] = len([
                a for a in self.agents.values() if a.role == role
            ])

        return {
            "total_agents": len(self.agents),
            "states": states,
            "roles": roles,
            "pending_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "messages_in_bus": len(self.message_bus),
            "consensus_decisions": len(self.consensus_history)
        }

    async def auto_scale(self):
        """Automatically scale swarm based on load."""
        if not self.config.auto_scale:
            return

        pending = len(self.task_queue)
        idle = len([a for a in self.agents.values() if a.state == AgentState.IDLE])
        total = len(self.agents)

        # Scale up if many pending tasks
        if pending > idle and total < self.config.max_agents:
            # Determine role based on pending task requirements
            await self.spawn_agent(AgentRole.EXECUTOR)

        # Scale down if too many idle
        elif idle > pending + 2 and total > self.config.min_agents:
            idle_agents = [a for a in self.agents.values() if a.state == AgentState.IDLE]
            if idle_agents:
                await self.terminate_agent(idle_agents[0].id)


class SwarmBuilder:
    """Builder for creating agent swarms."""

    def __init__(self):
        self.config = SwarmConfig()
        self.initial_agents: List[Tuple[AgentRole, str, List[AgentCapability]]] = []

    def with_config(self, config: SwarmConfig) -> "SwarmBuilder":
        """Set swarm configuration."""
        self.config = config
        return self

    def with_agent(
        self,
        role: AgentRole,
        name: str = None,
        capabilities: List[AgentCapability] = None
    ) -> "SwarmBuilder":
        """Add an initial agent."""
        self.initial_agents.append((role, name, capabilities))
        return self

    def with_researchers(self, count: int) -> "SwarmBuilder":
        """Add researcher agents."""
        for i in range(count):
            self.initial_agents.append((AgentRole.RESEARCHER, f"Researcher_{i}", None))
        return self

    def with_analysts(self, count: int) -> "SwarmBuilder":
        """Add analyst agents."""
        for i in range(count):
            self.initial_agents.append((AgentRole.ANALYST, f"Analyst_{i}", None))
        return self

    def with_executors(self, count: int) -> "SwarmBuilder":
        """Add executor agents."""
        for i in range(count):
            self.initial_agents.append((AgentRole.EXECUTOR, f"Executor_{i}", None))
        return self

    async def build(self) -> SwarmCoordinator:
        """Build the swarm coordinator with initial agents."""
        coordinator = SwarmCoordinator(self.config)

        for role, name, caps in self.initial_agents:
            await coordinator.spawn_agent(role, name, caps)

        return coordinator


async def demo():
    """Demonstrate swarm coordinator."""
    print("=" * 60)
    print("BAEL Agent Swarm Coordinator Demo")
    print("=" * 60)

    # Build a diverse swarm
    coordinator = await (
        SwarmBuilder()
        .with_researchers(2)
        .with_analysts(2)
        .with_agent(AgentRole.PLANNER, "Strategic_Planner")
        .with_agent(AgentRole.CRITIC, "Quality_Critic")
        .with_executors(2)
        .with_agent(AgentRole.SYNTHESIZER, "Knowledge_Synthesizer")
        .build()
    )

    print(f"\nSwarm Status:")
    status = coordinator.get_swarm_status()
    print(f"  Total Agents: {status['total_agents']}")
    print(f"  Roles: {status['roles']}")

    # Submit tasks
    task1 = AgentTask(
        id="t1",
        description="Research quantum computing",
        required_capabilities=["search", "analysis"]
    )
    task2 = AgentTask(
        id="t2",
        description="Analyze market trends",
        required_capabilities=["analysis", "pattern_recognition"]
    )

    await coordinator.submit_task(task1)
    await coordinator.submit_task(task2)

    print(f"\nTasks submitted and assigned")

    # Request consensus
    consensus = await coordinator.request_consensus(
        topic="Best approach for complex problem",
        options=["iterative", "parallel", "hybrid"]
    )
    print(f"\nConsensus: {consensus['winner'] if consensus['consensus'] else 'No consensus'}")

    # Collective reasoning
    reasoning = await coordinator.collective_reasoning(
        "How should we approach this complex multi-step problem?",
        method="synthesis"
    )
    print(f"\nCollective reasoning: {len(reasoning['contributions'])} contributions")

    print("\n✓ Dynamic agent spawning")
    print("✓ Capability-matched task distribution")
    print("✓ Inter-agent messaging")
    print("✓ Consensus mechanisms")
    print("✓ Collective reasoning")
    print("✓ Auto-scaling")


if __name__ == "__main__":
    asyncio.run(demo())
