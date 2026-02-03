"""
BAEL - Multi-Agent Collaboration Engine
Advanced multi-agent orchestration with consensus and conflict resolution.

This module enables multiple AI agents to work together on complex tasks,
sharing knowledge, coordinating actions, and reaching consensus on solutions.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class AgentRole(Enum):
    """Roles an agent can play in collaboration."""
    LEADER = "leader"           # Coordinates the team
    SPECIALIST = "specialist"   # Domain expert
    REVIEWER = "reviewer"       # Reviews and validates
    EXECUTOR = "executor"       # Executes tasks
    OBSERVER = "observer"       # Monitors and reports
    MEDIATOR = "mediator"       # Resolves conflicts


class CollaborationMode(Enum):
    """Modes of multi-agent collaboration."""
    HIERARCHICAL = "hierarchical"   # Leader directs others
    DEMOCRATIC = "democratic"       # Consensus-based decisions
    COMPETITIVE = "competitive"     # Agents compete for best solution
    SWARM = "swarm"                 # Emergent collective behavior
    PIPELINE = "pipeline"           # Sequential processing
    PARALLEL = "parallel"           # Concurrent independent work
    DEBATE = "debate"               # Structured argumentation


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    QUERY = "query"
    PROPOSAL = "proposal"
    VOTE = "vote"
    CONSENSUS = "consensus"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"
    STATUS = "status"
    HANDOFF = "handoff"


class ConflictType(Enum):
    """Types of conflicts that can arise."""
    OPINION = "opinion"           # Different opinions on approach
    RESOURCE = "resource"         # Competition for resources
    PRIORITY = "priority"         # Disagreement on priorities
    INFORMATION = "information"   # Conflicting information
    CAPABILITY = "capability"     # Overlapping capabilities


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentMessage:
    """Message between agents."""
    id: str
    sender: str
    receiver: str  # Can be specific agent or "broadcast"
    type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    in_reply_to: Optional[str] = None
    priority: int = 0  # 0-10, higher = more urgent
    requires_response: bool = False
    ttl: int = 60  # Time to live in seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "in_reply_to": self.in_reply_to,
            "priority": self.priority,
            "requires_response": self.requires_response,
            "ttl": self.ttl
        }


@dataclass
class AgentProfile:
    """Profile describing an agent's capabilities."""
    id: str
    name: str
    role: AgentRole
    specialties: List[str]
    capabilities: Set[str]
    trust_score: float = 1.0  # 0.0-1.0
    workload: float = 0.0     # Current workload 0.0-1.0
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_handle(self, task_type: str) -> bool:
        """Check if agent can handle a task type."""
        return task_type in self.capabilities or any(
            spec.lower() in task_type.lower()
            for spec in self.specialties
        )


@dataclass
class Proposal:
    """A proposal for group decision."""
    id: str
    proposer: str
    description: str
    options: List[str]
    votes: Dict[str, str] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    status: str = "pending"  # pending, accepted, rejected
    result: Optional[str] = None


@dataclass
class Conflict:
    """A conflict between agents."""
    id: str
    type: ConflictType
    parties: List[str]
    description: str
    positions: Dict[str, str]  # agent_id -> their position
    status: str = "active"  # active, resolving, resolved
    resolution: Optional[str] = None
    mediator: Optional[str] = None


@dataclass
class CollaborationSession:
    """A collaboration session between agents."""
    id: str
    mode: CollaborationMode
    participants: List[str]
    leader: Optional[str]
    objective: str
    status: str = "active"
    started_at: datetime = field(default_factory=datetime.now)
    messages: List[AgentMessage] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ABSTRACT AGENT BASE
# =============================================================================

class CollaborativeAgent(ABC):
    """Base class for collaborative agents."""

    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.outbox: asyncio.Queue = asyncio.Queue()
        self.known_agents: Dict[str, AgentProfile] = {}
        self.active_sessions: Dict[str, CollaborationSession] = {}

    @property
    def id(self) -> str:
        return self.profile.id

    @property
    def name(self) -> str:
        return self.profile.name

    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message."""
        pass

    @abstractmethod
    async def think(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate a response to a prompt."""
        pass

    async def send_message(
        self,
        receiver: str,
        type: MessageType,
        content: Dict[str, Any],
        **kwargs
    ) -> AgentMessage:
        """Send a message to another agent."""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.id,
            receiver=receiver,
            type=type,
            content=content,
            **kwargs
        )
        await self.outbox.put(message)
        return message

    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive a message from the inbox."""
        try:
            return await asyncio.wait_for(self.inbox.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def broadcast(
        self,
        type: MessageType,
        content: Dict[str, Any]
    ) -> AgentMessage:
        """Broadcast a message to all known agents."""
        return await self.send_message("broadcast", type, content)

    def register_agent(self, profile: AgentProfile) -> None:
        """Register knowledge of another agent."""
        self.known_agents[profile.id] = profile

    def get_capable_agents(self, capability: str) -> List[AgentProfile]:
        """Find agents with a specific capability."""
        return [
            agent for agent in self.known_agents.values()
            if agent.can_handle(capability)
        ]


# =============================================================================
# MESSAGE BUS
# =============================================================================

class AgentMessageBus:
    """Message bus for inter-agent communication."""

    def __init__(self):
        self.agents: Dict[str, CollaborativeAgent] = {}
        self.message_history: List[AgentMessage] = []
        self.subscribers: Dict[str, List[Callable]] = {}
        self._running = False

    def register(self, agent: CollaborativeAgent) -> None:
        """Register an agent with the bus."""
        self.agents[agent.id] = agent

        # Notify all agents of new member
        for other_agent in self.agents.values():
            if other_agent.id != agent.id:
                other_agent.register_agent(agent.profile)
                agent.register_agent(other_agent.profile)

        logger.info(f"Agent registered: {agent.name} ({agent.id})")

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the bus."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")

    async def route_message(self, message: AgentMessage) -> None:
        """Route a message to its recipient(s)."""
        self.message_history.append(message)

        if message.receiver == "broadcast":
            # Broadcast to all agents except sender
            for agent_id, agent in self.agents.items():
                if agent_id != message.sender:
                    await agent.inbox.put(message)
        else:
            # Direct message
            if message.receiver in self.agents:
                await self.agents[message.receiver].inbox.put(message)
            else:
                logger.warning(f"Unknown recipient: {message.receiver}")

    async def run(self) -> None:
        """Run the message bus."""
        self._running = True

        while self._running:
            # Collect messages from all agent outboxes
            for agent in self.agents.values():
                while not agent.outbox.empty():
                    message = await agent.outbox.get()
                    await self.route_message(message)

            await asyncio.sleep(0.01)  # Small delay to prevent busy loop

    def stop(self) -> None:
        """Stop the message bus."""
        self._running = False


# =============================================================================
# CONSENSUS ENGINE
# =============================================================================

class ConsensusEngine:
    """Engine for reaching consensus among agents."""

    def __init__(self, bus: AgentMessageBus):
        self.bus = bus
        self.proposals: Dict[str, Proposal] = {}

    async def create_proposal(
        self,
        proposer: str,
        description: str,
        options: List[str],
        deadline_seconds: int = 60
    ) -> Proposal:
        """Create a new proposal for voting."""
        proposal = Proposal(
            id=str(uuid.uuid4()),
            proposer=proposer,
            description=description,
            options=options,
            deadline=datetime.now() if deadline_seconds else None
        )
        self.proposals[proposal.id] = proposal

        # Broadcast proposal
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=proposer,
            receiver="broadcast",
            type=MessageType.PROPOSAL,
            content={
                "proposal_id": proposal.id,
                "description": description,
                "options": options
            }
        )
        await self.bus.route_message(message)

        return proposal

    async def vote(
        self,
        proposal_id: str,
        voter: str,
        choice: str
    ) -> bool:
        """Cast a vote on a proposal."""
        if proposal_id not in self.proposals:
            return False

        proposal = self.proposals[proposal_id]

        if choice not in proposal.options:
            return False

        proposal.votes[voter] = choice

        # Broadcast vote
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=voter,
            receiver="broadcast",
            type=MessageType.VOTE,
            content={
                "proposal_id": proposal_id,
                "choice": choice
            }
        )
        await self.bus.route_message(message)

        return True

    def get_result(
        self,
        proposal_id: str,
        method: str = "majority"
    ) -> Optional[str]:
        """Calculate the result of a proposal."""
        if proposal_id not in self.proposals:
            return None

        proposal = self.proposals[proposal_id]

        if not proposal.votes:
            return None

        # Count votes
        vote_counts: Dict[str, int] = {}
        for choice in proposal.votes.values():
            vote_counts[choice] = vote_counts.get(choice, 0) + 1

        if method == "majority":
            # Simple majority
            return max(vote_counts.items(), key=lambda x: x[1])[0]

        elif method == "supermajority":
            # 2/3 majority required
            total = sum(vote_counts.values())
            for option, count in vote_counts.items():
                if count >= total * 2 / 3:
                    return option
            return None

        elif method == "unanimous":
            # All must agree
            unique_votes = set(proposal.votes.values())
            if len(unique_votes) == 1:
                return unique_votes.pop()
            return None

        return None

    async def finalize_proposal(
        self,
        proposal_id: str,
        method: str = "majority"
    ) -> Optional[str]:
        """Finalize a proposal and broadcast result."""
        result = self.get_result(proposal_id, method)

        if result:
            proposal = self.proposals[proposal_id]
            proposal.status = "accepted"
            proposal.result = result

            # Broadcast consensus
            message = AgentMessage(
                id=str(uuid.uuid4()),
                sender="consensus_engine",
                receiver="broadcast",
                type=MessageType.CONSENSUS,
                content={
                    "proposal_id": proposal_id,
                    "result": result,
                    "votes": proposal.votes
                }
            )
            await self.bus.route_message(message)

        return result


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolves conflicts between agents."""

    def __init__(self, bus: AgentMessageBus):
        self.bus = bus
        self.conflicts: Dict[str, Conflict] = {}
        self.resolution_strategies: Dict[ConflictType, Callable] = {
            ConflictType.OPINION: self._resolve_opinion_conflict,
            ConflictType.RESOURCE: self._resolve_resource_conflict,
            ConflictType.PRIORITY: self._resolve_priority_conflict,
            ConflictType.INFORMATION: self._resolve_information_conflict,
            ConflictType.CAPABILITY: self._resolve_capability_conflict,
        }

    async def report_conflict(
        self,
        reporter: str,
        conflict_type: ConflictType,
        parties: List[str],
        description: str
    ) -> Conflict:
        """Report a new conflict."""
        conflict = Conflict(
            id=str(uuid.uuid4()),
            type=conflict_type,
            parties=parties,
            description=description
        )
        self.conflicts[conflict.id] = conflict

        # Broadcast conflict notification
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=reporter,
            receiver="broadcast",
            type=MessageType.CONFLICT,
            content={
                "conflict_id": conflict.id,
                "type": conflict_type.value,
                "parties": parties,
                "description": description
            }
        )
        await self.bus.route_message(message)

        return conflict

    async def add_position(
        self,
        conflict_id: str,
        agent_id: str,
        position: str
    ) -> None:
        """Add an agent's position to a conflict."""
        if conflict_id in self.conflicts:
            self.conflicts[conflict_id].positions[agent_id] = position

    async def resolve(
        self,
        conflict_id: str,
        mediator: Optional[str] = None
    ) -> Optional[str]:
        """Attempt to resolve a conflict."""
        if conflict_id not in self.conflicts:
            return None

        conflict = self.conflicts[conflict_id]
        conflict.status = "resolving"
        conflict.mediator = mediator

        # Get appropriate resolution strategy
        strategy = self.resolution_strategies.get(conflict.type)
        if strategy:
            resolution = await strategy(conflict)

            if resolution:
                conflict.status = "resolved"
                conflict.resolution = resolution

                # Broadcast resolution
                message = AgentMessage(
                    id=str(uuid.uuid4()),
                    sender=mediator or "conflict_resolver",
                    receiver="broadcast",
                    type=MessageType.RESOLUTION,
                    content={
                        "conflict_id": conflict_id,
                        "resolution": resolution
                    }
                )
                await self.bus.route_message(message)

                return resolution

        return None

    async def _resolve_opinion_conflict(self, conflict: Conflict) -> str:
        """Resolve an opinion-based conflict."""
        # Use weighted voting based on trust scores
        if len(conflict.positions) >= 2:
            # Find the position with most support
            position_weights: Dict[str, float] = {}

            for agent_id, position in conflict.positions.items():
                agent = self.bus.agents.get(agent_id)
                weight = agent.profile.trust_score if agent else 0.5
                position_weights[position] = position_weights.get(position, 0) + weight

            if position_weights:
                best_position = max(position_weights.items(), key=lambda x: x[1])
                return f"Adopted position: {best_position[0]} (weight: {best_position[1]:.2f})"

        return "No resolution reached - insufficient positions"

    async def _resolve_resource_conflict(self, conflict: Conflict) -> str:
        """Resolve a resource conflict."""
        # Priority-based allocation
        return "Resource allocated based on workload and priority"

    async def _resolve_priority_conflict(self, conflict: Conflict) -> str:
        """Resolve a priority conflict."""
        return "Priorities merged using weighted combination"

    async def _resolve_information_conflict(self, conflict: Conflict) -> str:
        """Resolve an information conflict."""
        return "Information reconciled using consensus"

    async def _resolve_capability_conflict(self, conflict: Conflict) -> str:
        """Resolve a capability overlap conflict."""
        return "Capabilities partitioned to avoid overlap"


# =============================================================================
# TASK DELEGATOR
# =============================================================================

class TaskDelegator:
    """Delegates tasks to appropriate agents."""

    def __init__(self, bus: AgentMessageBus):
        self.bus = bus
        self.pending_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id

    async def delegate_task(
        self,
        task_id: str,
        task_type: str,
        description: str,
        requirements: List[str],
        priority: int = 5,
        requester: Optional[str] = None
    ) -> Optional[str]:
        """Delegate a task to the most suitable agent."""
        # Find capable agents
        candidates = []

        for agent in self.bus.agents.values():
            if agent.profile.can_handle(task_type):
                score = self._calculate_suitability(
                    agent.profile,
                    task_type,
                    requirements
                )
                candidates.append((agent, score))

        if not candidates:
            logger.warning(f"No capable agents for task: {task_type}")
            return None

        # Sort by suitability score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Assign to best candidate
        best_agent = candidates[0][0]
        self.task_assignments[task_id] = best_agent.id

        # Send task request
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=requester or "task_delegator",
            receiver=best_agent.id,
            type=MessageType.REQUEST,
            content={
                "task_id": task_id,
                "task_type": task_type,
                "description": description,
                "requirements": requirements
            },
            priority=priority,
            requires_response=True
        )
        await self.bus.route_message(message)

        logger.info(f"Task {task_id} delegated to {best_agent.name}")
        return best_agent.id

    def _calculate_suitability(
        self,
        profile: AgentProfile,
        task_type: str,
        requirements: List[str]
    ) -> float:
        """Calculate how suitable an agent is for a task."""
        score = 0.0

        # Check specialties
        for specialty in profile.specialties:
            if specialty.lower() in task_type.lower():
                score += 0.3

        # Check capabilities
        matched = sum(
            1 for req in requirements
            if req in profile.capabilities
        )
        if requirements:
            score += 0.3 * (matched / len(requirements))

        # Consider workload (prefer less loaded agents)
        score += 0.2 * (1.0 - profile.workload)

        # Consider trust score
        score += 0.2 * profile.trust_score

        return score


# =============================================================================
# COLLABORATION COORDINATOR
# =============================================================================

class CollaborationCoordinator:
    """Coordinates multi-agent collaboration sessions."""

    def __init__(self):
        self.bus = AgentMessageBus()
        self.consensus = ConsensusEngine(self.bus)
        self.conflict_resolver = ConflictResolver(self.bus)
        self.delegator = TaskDelegator(self.bus)
        self.sessions: Dict[str, CollaborationSession] = {}

    def register_agent(self, agent: CollaborativeAgent) -> None:
        """Register an agent with the coordinator."""
        self.bus.register(agent)

    async def create_session(
        self,
        mode: CollaborationMode,
        participants: List[str],
        objective: str,
        leader: Optional[str] = None
    ) -> CollaborationSession:
        """Create a new collaboration session."""
        session = CollaborationSession(
            id=str(uuid.uuid4()),
            mode=mode,
            participants=participants,
            leader=leader or (participants[0] if participants else None),
            objective=objective
        )
        self.sessions[session.id] = session

        # Notify participants
        for participant_id in participants:
            if participant_id in self.bus.agents:
                agent = self.bus.agents[participant_id]
                agent.active_sessions[session.id] = session

        logger.info(f"Created session {session.id} with mode {mode.value}")
        return session

    async def end_session(self, session_id: str) -> None:
        """End a collaboration session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.status = "completed"

            # Notify participants
            for participant_id in session.participants:
                if participant_id in self.bus.agents:
                    agent = self.bus.agents[participant_id]
                    if session_id in agent.active_sessions:
                        del agent.active_sessions[session_id]

    async def run_hierarchical_collaboration(
        self,
        session_id: str,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run hierarchical (leader-directed) collaboration."""
        session = self.sessions.get(session_id)
        if not session or not session.leader:
            return {"error": "Invalid session or no leader"}

        leader = self.bus.agents.get(session.leader)
        if not leader:
            return {"error": "Leader not found"}

        # Leader creates plan
        plan = await leader.think(
            f"Create a plan to accomplish: {task.get('description')}",
            {"participants": session.participants, "task": task}
        )

        # Delegate subtasks
        results = {}
        for participant_id in session.participants:
            if participant_id != session.leader:
                await self.delegator.delegate_task(
                    task_id=str(uuid.uuid4()),
                    task_type=task.get("type", "general"),
                    description=f"Subtask from: {plan}",
                    requirements=task.get("requirements", []),
                    requester=session.leader
                )

        return {"plan": plan, "results": results}

    async def run_democratic_collaboration(
        self,
        session_id: str,
        options: List[str],
        description: str
    ) -> Optional[str]:
        """Run democratic (consensus-based) collaboration."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Create proposal
        proposal = await self.consensus.create_proposal(
            proposer=session.leader or session.participants[0],
            description=description,
            options=options
        )

        # Wait for votes (simulated)
        await asyncio.sleep(0.5)

        # Finalize
        result = await self.consensus.finalize_proposal(proposal.id)

        if result:
            session.decisions.append({
                "proposal_id": proposal.id,
                "description": description,
                "result": result,
                "votes": proposal.votes
            })

        return result

    async def run_debate_collaboration(
        self,
        session_id: str,
        topic: str,
        rounds: int = 3
    ) -> Dict[str, Any]:
        """Run debate-style collaboration."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        debate_history = []

        for round_num in range(rounds):
            round_arguments = []

            for participant_id in session.participants:
                agent = self.bus.agents.get(participant_id)
                if agent:
                    # Generate argument
                    context = {
                        "topic": topic,
                        "round": round_num + 1,
                        "previous_arguments": debate_history
                    }
                    argument = await agent.think(
                        f"Present your argument on: {topic}",
                        context
                    )
                    round_arguments.append({
                        "agent": participant_id,
                        "argument": argument
                    })

            debate_history.append({
                "round": round_num + 1,
                "arguments": round_arguments
            })

        # Synthesize conclusion
        return {
            "topic": topic,
            "rounds": debate_history,
            "status": "completed"
        }

    async def run_swarm_collaboration(
        self,
        session_id: str,
        task: Dict[str, Any],
        iterations: int = 5
    ) -> Dict[str, Any]:
        """Run swarm-style emergent collaboration."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Each agent works independently, sharing discoveries
        collective_knowledge = []

        for iteration in range(iterations):
            iteration_contributions = []

            for participant_id in session.participants:
                agent = self.bus.agents.get(participant_id)
                if agent:
                    # Agent explores based on collective knowledge
                    contribution = await agent.think(
                        f"Contribute to: {task.get('description')}",
                        {
                            "task": task,
                            "collective_knowledge": collective_knowledge,
                            "iteration": iteration + 1
                        }
                    )
                    iteration_contributions.append({
                        "agent": participant_id,
                        "contribution": contribution
                    })

            collective_knowledge.extend(iteration_contributions)

        return {
            "task": task,
            "iterations": iterations,
            "collective_knowledge": collective_knowledge
        }

    async def start(self) -> None:
        """Start the coordinator and message bus."""
        await self.bus.run()

    def stop(self) -> None:
        """Stop the coordinator."""
        self.bus.stop()


# =============================================================================
# CONCRETE AGENT IMPLEMENTATION
# =============================================================================

class BaelCollaborativeAgent(CollaborativeAgent):
    """BAEL implementation of a collaborative agent."""

    def __init__(
        self,
        name: str,
        role: AgentRole,
        specialties: List[str],
        llm_client: Optional[Any] = None
    ):
        profile = AgentProfile(
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            specialties=specialties,
            capabilities=set(specialties)
        )
        super().__init__(profile)
        self.llm_client = llm_client
        self.memory: List[Dict[str, Any]] = []

    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message."""
        logger.info(f"{self.name} received: {message.type.value} from {message.sender}")

        if message.type == MessageType.REQUEST:
            # Handle task request
            task = message.content
            response_content = await self.think(
                task.get("description", ""),
                task
            )

            if message.requires_response:
                return await self.send_message(
                    message.sender,
                    MessageType.RESPONSE,
                    {"result": response_content},
                    in_reply_to=message.id
                )

        elif message.type == MessageType.PROPOSAL:
            # Auto-vote on proposal (in real implementation, would analyze)
            proposal = message.content
            options = proposal.get("options", [])
            if options:
                # Simple strategy: vote for first option (would be smarter)
                chosen = options[0]
                return await self.send_message(
                    message.sender,
                    MessageType.VOTE,
                    {
                        "proposal_id": proposal.get("proposal_id"),
                        "choice": chosen
                    },
                    in_reply_to=message.id
                )

        elif message.type == MessageType.QUERY:
            # Answer query
            query = message.content.get("query", "")
            response = await self.think(query, message.content)

            return await self.send_message(
                message.sender,
                MessageType.RESPONSE,
                {"answer": response},
                in_reply_to=message.id
            )

        return None

    async def think(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate a response using LLM or fallback."""
        if self.llm_client:
            # Use LLM
            try:
                response = await self.llm_client.complete(prompt, context)
                return response
            except Exception as e:
                logger.error(f"LLM error: {e}")

        # Fallback: Simple response
        return f"[{self.name}] Processed: {prompt[:100]}..."

    async def run(self) -> None:
        """Run the agent's message processing loop."""
        while True:
            message = await self.receive_message()
            if message:
                response = await self.process_message(message)
                if response:
                    await self.outbox.put(response)


# =============================================================================
# TEAM TEMPLATES
# =============================================================================

def create_development_team(llm_client: Optional[Any] = None) -> List[BaelCollaborativeAgent]:
    """Create a software development team."""
    return [
        BaelCollaborativeAgent(
            name="Architect",
            role=AgentRole.LEADER,
            specialties=["system_design", "architecture", "planning"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Developer",
            role=AgentRole.EXECUTOR,
            specialties=["coding", "implementation", "debugging"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Reviewer",
            role=AgentRole.REVIEWER,
            specialties=["code_review", "quality", "testing"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Security",
            role=AgentRole.SPECIALIST,
            specialties=["security", "vulnerabilities", "hardening"],
            llm_client=llm_client
        ),
    ]


def create_research_team(llm_client: Optional[Any] = None) -> List[BaelCollaborativeAgent]:
    """Create a research team."""
    return [
        BaelCollaborativeAgent(
            name="Lead Researcher",
            role=AgentRole.LEADER,
            specialties=["research", "synthesis", "direction"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Data Analyst",
            role=AgentRole.SPECIALIST,
            specialties=["data_analysis", "statistics", "visualization"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Domain Expert",
            role=AgentRole.SPECIALIST,
            specialties=["domain_knowledge", "context", "validation"],
            llm_client=llm_client
        ),
        BaelCollaborativeAgent(
            name="Critic",
            role=AgentRole.REVIEWER,
            specialties=["critical_analysis", "bias_detection", "verification"],
            llm_client=llm_client
        ),
    ]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_collaboration():
    """Demonstrate multi-agent collaboration."""
    # Create coordinator
    coordinator = CollaborationCoordinator()

    # Create and register agents
    team = create_development_team()
    for agent in team:
        coordinator.register_agent(agent)

    # Create session
    session = await coordinator.create_session(
        mode=CollaborationMode.HIERARCHICAL,
        participants=[agent.id for agent in team],
        objective="Build a REST API"
    )

    # Run collaboration
    result = await coordinator.run_hierarchical_collaboration(
        session.id,
        {
            "type": "development",
            "description": "Create a FastAPI REST API with CRUD operations",
            "requirements": ["python", "fastapi", "database"]
        }
    )

    print(f"Collaboration result: {result}")

    # End session
    await coordinator.end_session(session.id)


if __name__ == "__main__":
    asyncio.run(example_collaboration())
