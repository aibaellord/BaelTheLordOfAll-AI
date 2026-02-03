"""
BAEL - Multi-Agent Collaboration Protocol
Advanced protocols for agent-to-agent communication, task delegation, and consensus.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger("BAEL.Collaboration")


# =============================================================================
# PROTOCOL ENUMS
# =============================================================================

class MessageType(Enum):
    """Types of messages in the collaboration protocol."""
    # Task-related
    TASK_PROPOSAL = "task_proposal"
    TASK_ACCEPTED = "task_accepted"
    TASK_REJECTED = "task_rejected"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Communication
    REQUEST_INFO = "request_info"
    PROVIDE_INFO = "provide_info"
    REQUEST_HELP = "request_help"
    OFFER_HELP = "offer_help"

    # Coordination
    NEGOTIATE = "negotiate"
    VOTE = "vote"
    CONSENSUS_REACHED = "consensus_reached"
    CONFLICT = "conflict"
    RESOLVE_CONFLICT = "resolve_conflict"

    # Status
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    AGENT_JOINING = "agent_joining"
    AGENT_LEAVING = "agent_leaving"


class VotingStrategy(Enum):
    """Strategies for voting and consensus."""
    UNANIMOUS = "unanimous"          # All agents must agree
    MAJORITY = "majority"            # >50% must agree
    SUPERMAJORITY = "supermajority"  # >66% must agree
    WEIGHTED = "weighted"            # Votes weighted by agent expertise
    RANKED_CHOICE = "ranked_choice"  # Agents rank options


class DelegationStrategy(Enum):
    """Strategies for task delegation."""
    CAPABILITY_MATCH = "capability_match"    # Match by agent capabilities
    LOAD_BALANCE = "load_balance"           # Distribute evenly
    PRIORITY_BASED = "priority_based"        # High priority to most capable
    AUCTION = "auction"                      # Agents bid on tasks
    HIERARCHICAL = "hierarchical"            # Leader assigns tasks


# =============================================================================
# MESSAGE STRUCTURES
# =============================================================================

@dataclass
class AgentIdentity:
    """Identity information for an agent."""
    id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    trust_score: float = 1.0
    reputation: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationMessage:
    """Message in the collaboration protocol."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.REQUEST_INFO
    sender: str = ""
    recipients: List[str] = field(default_factory=list)  # Empty = broadcast
    subject: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    priority: int = 3  # 1-5, 5 is highest
    requires_response: bool = False
    deadline: Optional[datetime] = None


@dataclass
class TaskProposal:
    """Proposal for task delegation."""
    id: str
    task_description: str
    requirements: Dict[str, Any]
    constraints: Dict[str, Any]
    reward: float = 0.0
    deadline: Optional[datetime] = None
    proposer: str = ""
    potential_agents: List[str] = field(default_factory=list)


@dataclass
class Vote:
    """A vote in a consensus decision."""
    voter_id: str
    option: str
    weight: float = 1.0
    rationale: str = ""
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Consensus:
    """Result of a consensus process."""
    id: str
    question: str
    options: List[str]
    votes: List[Vote] = field(default_factory=list)
    strategy: VotingStrategy = VotingStrategy.MAJORITY
    winner: Optional[str] = None
    reached: bool = False
    confidence: float = 0.0


# =============================================================================
# COLLABORATION PROTOCOL
# =============================================================================

class CollaborationProtocol:
    """
    Manages multi-agent collaboration with advanced protocols.

    Features:
    - Message routing and delivery
    - Task delegation with multiple strategies
    - Consensus and voting mechanisms
    - Conflict resolution
    - Agent reputation tracking
    """

    def __init__(self):
        self.agents: Dict[str, AgentIdentity] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, TaskProposal] = {}
        self.active_consensus: Dict[str, Consensus] = {}
        self.message_history: List[CollaborationMessage] = []

        # Callbacks
        self.message_handlers: Dict[MessageType, List[asyncio.coroutine]] = {}

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_delegated": 0,
            "tasks_completed": 0,
            "consensus_reached": 0,
            "conflicts_resolved": 0
        }

    # =========================================================================
    # AGENT MANAGEMENT
    # =========================================================================

    def register_agent(self, agent: AgentIdentity):
        """Register an agent in the collaboration network."""
        self.agents[agent.id] = agent
        logger.info(f"✅ Agent registered: {agent.name} ({agent.id})")

        # Broadcast agent joining
        asyncio.create_task(self.broadcast_message(
            CollaborationMessage(
                type=MessageType.AGENT_JOINING,
                sender=agent.id,
                subject="Agent Joining",
                content={"agent": agent.name, "capabilities": agent.capabilities}
            )
        ))

    def unregister_agent(self, agent_id: str):
        """Remove an agent from the network."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            logger.info(f"❌ Agent unregistered: {agent.name} ({agent_id})")

            # Broadcast agent leaving
            asyncio.create_task(self.broadcast_message(
                CollaborationMessage(
                    type=MessageType.AGENT_LEAVING,
                    sender=agent_id,
                    subject="Agent Leaving",
                    content={"agent": agent.name}
                )
            ))

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def list_agents_by_capability(self, capability: str) -> List[AgentIdentity]:
        """Find agents with a specific capability."""
        return [
            agent for agent in self.agents.values()
            if capability in agent.capabilities
        ]

    # =========================================================================
    # MESSAGE HANDLING
    # =========================================================================

    async def send_message(self, message: CollaborationMessage):
        """Send a message to recipient(s)."""
        self.stats["messages_sent"] += 1
        self.message_history.append(message)

        logger.debug(f"📤 Message {message.id}: {message.type.value} from {message.sender}")

        # Add to queue for processing
        await self.message_queue.put(message)

        # Invoke registered handlers
        handlers = self.message_handlers.get(message.type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.type}: {e}")

    async def broadcast_message(self, message: CollaborationMessage):
        """Broadcast a message to all agents."""
        message.recipients = list(self.agents.keys())
        await self.send_message(message)

    def register_message_handler(
        self,
        message_type: MessageType,
        handler: asyncio.coroutine
    ):
        """Register a callback for a message type."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    async def process_messages(self):
        """Process messages from the queue (run in background)."""
        while True:
            try:
                message = await self.message_queue.get()
                self.stats["messages_received"] += 1

                # Route to recipients
                if message.recipients:
                    for recipient_id in message.recipients:
                        if recipient_id in self.agents:
                            # Deliver to agent (would integrate with actual agent)
                            logger.debug(f"📬 Delivering to {recipient_id}")

                self.message_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing message: {e}")

            await asyncio.sleep(0.01)  # Prevent tight loop

    # =========================================================================
    # TASK DELEGATION
    # =========================================================================

    async def delegate_task(
        self,
        proposal: TaskProposal,
        strategy: DelegationStrategy = DelegationStrategy.CAPABILITY_MATCH
    ) -> Optional[str]:
        """
        Delegate a task to the most appropriate agent.

        Returns:
            ID of agent that accepted the task, or None
        """
        self.active_tasks[proposal.id] = proposal
        self.stats["tasks_delegated"] += 1

        logger.info(f"🎯 Delegating task: {proposal.task_description}")

        # Select candidates based on strategy
        candidates = await self._select_candidates(proposal, strategy)

        if not candidates:
            logger.warning("No suitable candidates found for task")
            return None

        # Send proposal to candidates
        for candidate_id in candidates:
            await self.send_message(
                CollaborationMessage(
                    type=MessageType.TASK_PROPOSAL,
                    sender=proposal.proposer,
                    recipients=[candidate_id],
                    subject="Task Proposal",
                    content={
                        "proposal_id": proposal.id,
                        "task": proposal.task_description,
                        "requirements": proposal.requirements,
                        "reward": proposal.reward,
                        "deadline": proposal.deadline.isoformat() if proposal.deadline else None
                    },
                    requires_response=True,
                    deadline=proposal.deadline
                )
            )

        # Wait for acceptance (simplified - would be event-driven)
        # In real implementation, would use callbacks/events
        return candidates[0] if candidates else None

    async def _select_candidates(
        self,
        proposal: TaskProposal,
        strategy: DelegationStrategy
    ) -> List[str]:
        """Select candidate agents based on delegation strategy."""

        if strategy == DelegationStrategy.CAPABILITY_MATCH:
            # Match by required capabilities
            required_caps = proposal.requirements.get("capabilities", [])
            candidates = [
                agent.id for agent in self.agents.values()
                if all(cap in agent.capabilities for cap in required_caps)
            ]
            # Sort by reputation
            candidates.sort(
                key=lambda aid: self.agents[aid].reputation,
                reverse=True
            )
            return candidates[:3]  # Top 3

        elif strategy == DelegationStrategy.LOAD_BALANCE:
            # Would integrate with actual agent load metrics
            return list(self.agents.keys())[:3]

        elif strategy == DelegationStrategy.PRIORITY_BASED:
            # Assign to highest reputation agent
            sorted_agents = sorted(
                self.agents.values(),
                key=lambda a: (a.reputation, a.trust_score),
                reverse=True
            )
            return [sorted_agents[0].id] if sorted_agents else []

        else:
            # Default: all agents
            return list(self.agents.keys())

    async def accept_task(self, agent_id: str, proposal_id: str):
        """Agent accepts a task proposal."""
        if proposal_id not in self.active_tasks:
            return

        proposal = self.active_tasks[proposal_id]

        await self.send_message(
            CollaborationMessage(
                type=MessageType.TASK_ACCEPTED,
                sender=agent_id,
                recipients=[proposal.proposer],
                subject="Task Accepted",
                content={"proposal_id": proposal_id}
            )
        )

        logger.info(f"✅ Task {proposal_id} accepted by {agent_id}")

    async def complete_task(
        self,
        agent_id: str,
        proposal_id: str,
        result: Any
    ):
        """Agent reports task completion."""
        if proposal_id not in self.active_tasks:
            return

        proposal = self.active_tasks[proposal_id]
        del self.active_tasks[proposal_id]
        self.stats["tasks_completed"] += 1

        # Update agent reputation
        if agent_id in self.agents:
            self.agents[agent_id].reputation = min(
                1.0,
                self.agents[agent_id].reputation + 0.01
            )

        await self.send_message(
            CollaborationMessage(
                type=MessageType.TASK_COMPLETED,
                sender=agent_id,
                recipients=[proposal.proposer],
                subject="Task Completed",
                content={
                    "proposal_id": proposal_id,
                    "result": result
                }
            )
        )

        logger.info(f"✅ Task {proposal_id} completed by {agent_id}")

    # =========================================================================
    # CONSENSUS & VOTING
    # =========================================================================

    async def initiate_consensus(
        self,
        question: str,
        options: List[str],
        strategy: VotingStrategy = VotingStrategy.MAJORITY,
        participants: Optional[List[str]] = None
    ) -> str:
        """
        Initiate a consensus process.

        Returns:
            Consensus ID
        """
        consensus_id = str(uuid4())
        consensus = Consensus(
            id=consensus_id,
            question=question,
            options=options,
            strategy=strategy
        )

        self.active_consensus[consensus_id] = consensus

        # Send voting request
        recipients = participants or list(self.agents.keys())

        await self.send_message(
            CollaborationMessage(
                type=MessageType.VOTE,
                sender="system",
                recipients=recipients,
                subject="Vote Request",
                content={
                    "consensus_id": consensus_id,
                    "question": question,
                    "options": options,
                    "strategy": strategy.value
                },
                requires_response=True
            )
        )

        logger.info(f"🗳️ Consensus initiated: {question}")

        return consensus_id

    async def cast_vote(
        self,
        consensus_id: str,
        voter_id: str,
        option: str,
        rationale: str = "",
        confidence: float = 1.0
    ):
        """Cast a vote in a consensus process."""
        if consensus_id not in self.active_consensus:
            return

        consensus = self.active_consensus[consensus_id]

        # Calculate vote weight
        weight = 1.0
        if consensus.strategy == VotingStrategy.WEIGHTED:
            # Weight by agent reputation
            agent = self.agents.get(voter_id)
            weight = agent.reputation if agent else 1.0

        vote = Vote(
            voter_id=voter_id,
            option=option,
            weight=weight,
            rationale=rationale,
            confidence=confidence
        )

        consensus.votes.append(vote)

        logger.info(f"🗳️ Vote cast by {voter_id}: {option} (weight={weight:.2f})")

        # Check if consensus reached
        await self._check_consensus(consensus_id)

    async def _check_consensus(self, consensus_id: str):
        """Check if consensus has been reached."""
        consensus = self.active_consensus[consensus_id]

        # Count votes
        vote_counts: Dict[str, float] = {opt: 0.0 for opt in consensus.options}
        total_weight = 0.0

        for vote in consensus.votes:
            if vote.option in vote_counts:
                vote_counts[vote.option] += vote.weight
                total_weight += vote.weight

        if total_weight == 0:
            return

        # Determine winner based on strategy
        winner = max(vote_counts.items(), key=lambda x: x[1])
        winner_option, winner_votes = winner

        reached = False

        if consensus.strategy == VotingStrategy.UNANIMOUS:
            reached = winner_votes == total_weight
        elif consensus.strategy == VotingStrategy.MAJORITY:
            reached = winner_votes > total_weight / 2
        elif consensus.strategy == VotingStrategy.SUPERMAJORITY:
            reached = winner_votes > total_weight * 0.66
        elif consensus.strategy == VotingStrategy.WEIGHTED:
            reached = winner_votes > total_weight / 2

        if reached:
            consensus.reached = True
            consensus.winner = winner_option
            consensus.confidence = winner_votes / total_weight

            self.stats["consensus_reached"] += 1

            # Broadcast consensus
            await self.broadcast_message(
                CollaborationMessage(
                    type=MessageType.CONSENSUS_REACHED,
                    sender="system",
                    subject="Consensus Reached",
                    content={
                        "consensus_id": consensus_id,
                        "question": consensus.question,
                        "winner": winner_option,
                        "confidence": consensus.confidence,
                        "vote_counts": vote_counts
                    }
                )
            )

            logger.info(f"✅ Consensus reached: {winner_option} (confidence={consensus.confidence:.2f})")

    def get_consensus_result(self, consensus_id: str) -> Optional[Consensus]:
        """Get the result of a consensus process."""
        return self.active_consensus.get(consensus_id)

    # =========================================================================
    # STATISTICS & MONITORING
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get protocol statistics."""
        return {
            **self.stats,
            "active_agents": len(self.agents),
            "active_tasks": len(self.active_tasks),
            "active_consensus": len(self.active_consensus),
            "message_queue_size": self.message_queue.qsize()
        }

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {}

        # Count messages sent/received by this agent
        messages_sent = len([m for m in self.message_history if m.sender == agent_id])
        messages_received = len([
            m for m in self.message_history
            if agent_id in m.recipients
        ])

        return {
            "name": agent.name,
            "reputation": agent.reputation,
            "trust_score": agent.trust_score,
            "capabilities": len(agent.capabilities),
            "messages_sent": messages_sent,
            "messages_received": messages_received
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_agent_identity(
    name: str,
    capabilities: List[str],
    specializations: List[str] = None
) -> AgentIdentity:
    """Create a new agent identity."""
    return AgentIdentity(
        id=str(uuid4()),
        name=name,
        capabilities=capabilities,
        specializations=specializations or [],
        trust_score=1.0,
        reputation=0.5
    )


__all__ = [
    'CollaborationProtocol',
    'CollaborationMessage',
    'AgentIdentity',
    'TaskProposal',
    'Consensus',
    'Vote',
    'MessageType',
    'VotingStrategy',
    'DelegationStrategy',
    'create_agent_identity'
]
