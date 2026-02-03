"""
Multi-Agent Coordination System

Enables multiple agents to work together with:
- Consensus decision making
- Distributed task execution
- Shared knowledge base
- Conflict resolution
- Load balancing
- Collective intelligence

This creates swarm intelligence that surpasses single-agent systems.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CoordinationStrategy(Enum):
    """Strategy for coordinating multiple agents."""
    LEADER_FOLLOWER = "leader_follower"
    CONSENSUS = "consensus"
    AUCTION = "auction"
    SWARM = "swarm"
    HIERARCHICAL = "hierarchical"


class AgentRole(Enum):
    """Role an agent can play."""
    LEADER = "leader"
    SPECIALIST = "specialist"
    GENERALIST = "generalist"
    OBSERVER = "observer"
    COORDINATOR = "coordinator"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    BACKGROUND = 1


@dataclass
class CoordinatedTask:
    """Task to be executed by coordinated agents."""
    task_id: str
    description: str
    priority: TaskPriority
    required_capabilities: List[str]
    subtasks: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    assigned_agents: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    context: Dict = field(default_factory=dict)


@dataclass
class AgentBid:
    """Bid from an agent for a task."""
    agent_id: str
    task_id: str
    confidence: float  # 0.0-1.0
    estimated_duration: float  # seconds
    resource_cost: float  # arbitrary units
    reason: str


@dataclass
class ConsensusVote:
    """Vote from an agent on a decision."""
    agent_id: str
    decision_id: str
    vote: str  # yes, no, abstain
    confidence: float
    reasoning: str


class CoordinationEngine:
    """
    Engine for coordinating multiple agents.

    Enables agents to:
    - Share knowledge and learn collectively
    - Make consensus decisions
    - Distribute work optimally
    - Resolve conflicts
    - Adapt strategies dynamically
    """

    def __init__(
        self,
        strategy: CoordinationStrategy = CoordinationStrategy.CONSENSUS
    ):
        """Initialize coordination engine."""
        self.strategy = strategy
        self.agents: Dict[str, Any] = {}  # agent_id -> agent
        self.agent_roles: Dict[str, AgentRole] = {}
        self.tasks: Dict[str, CoordinatedTask] = {}
        self.shared_knowledge: Dict[str, Any] = {}
        self.coordination_history: List[Dict] = []

        logger.info(f"Coordination engine initialized with {strategy.value} strategy")

    def register_agent(self, agent_id: str, agent: Any, role: AgentRole):
        """Register an agent with the coordination system."""
        self.agents[agent_id] = agent
        self.agent_roles[agent_id] = role

        logger.info(f"Registered agent {agent_id} with role {role.value}")

    async def coordinate_task(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """
        Coordinate execution of a task across multiple agents.

        The coordination strategy determines how agents collaborate.
        """
        logger.info(f"Coordinating task: {task.description} (priority: {task.priority.name})")

        self.tasks[task.task_id] = task

        if self.strategy == CoordinationStrategy.CONSENSUS:
            result = await self._consensus_coordination(task)
        elif self.strategy == CoordinationStrategy.AUCTION:
            result = await self._auction_coordination(task)
        elif self.strategy == CoordinationStrategy.SWARM:
            result = await self._swarm_coordination(task)
        elif self.strategy == CoordinationStrategy.LEADER_FOLLOWER:
            result = await self._leader_follower_coordination(task)
        else:
            result = await self._hierarchical_coordination(task)

        self._record_coordination(task, result)

        return result

    async def _consensus_coordination(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """Coordinate using consensus decision making."""
        # Get capable agents
        capable_agents = self._find_capable_agents(task.required_capabilities)

        if not capable_agents:
            return {
                "status": "failed",
                "reason": "No capable agents available"
            }

        # Each agent proposes approach
        proposals = await self._collect_proposals(task, capable_agents)

        # Vote on best approach
        votes = await self._vote_on_proposals(proposals, capable_agents)

        # Select winning proposal
        winning_proposal = self._select_by_consensus(proposals, votes)

        # Execute with consensus
        logger.info(f"Executing with consensus: {winning_proposal['agent_id']}")

        assigned_agents = [winning_proposal["agent_id"]]
        for agent_id, vote in votes.items():
            if vote.vote == "yes" and agent_id not in assigned_agents:
                assigned_agents.append(agent_id)

        # Distribute execution
        results = await self._execute_distributed(task, assigned_agents)

        return {
            "status": "success",
            "strategy": "consensus",
            "winning_proposal": winning_proposal,
            "assigned_agents": assigned_agents,
            "votes": len(votes),
            "results": results
        }

    async def _auction_coordination(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """Coordinate using auction mechanism."""
        capable_agents = self._find_capable_agents(task.required_capabilities)

        if not capable_agents:
            return {
                "status": "failed",
                "reason": "No capable agents available"
            }

        # Collect bids
        bids = await self._collect_bids(task, capable_agents)

        # Select winning bid
        winning_bid = self._select_winning_bid(bids, task.priority)

        logger.info(f"Auction winner: {winning_bid.agent_id} "
                   f"(confidence: {winning_bid.confidence:.2f}, "
                   f"duration: {winning_bid.estimated_duration:.1f}s)")

        # Execute
        agent = self.agents[winning_bid.agent_id]
        result = await agent.execute_autonomous(
            {"task": task.description, "context": task.context}
        )

        return {
            "status": "success",
            "strategy": "auction",
            "winning_bid": {
                "agent_id": winning_bid.agent_id,
                "confidence": winning_bid.confidence,
                "duration": winning_bid.estimated_duration
            },
            "total_bids": len(bids),
            "result": result
        }

    async def _swarm_coordination(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """Coordinate using swarm intelligence."""
        all_agents = list(self.agents.keys())

        # Break into subtasks
        subtasks = self._decompose_task(task)

        logger.info(f"Swarm processing {len(subtasks)} subtasks with {len(all_agents)} agents")

        # Agents self-organize
        assignments = await self._swarm_self_organize(subtasks, all_agents)

        # Parallel execution with dynamic rebalancing
        results = await self._swarm_execute(assignments)

        # Aggregate results
        final_result = self._aggregate_swarm_results(results)

        return {
            "status": "success",
            "strategy": "swarm",
            "agents_used": len(set(a for a, _ in assignments)),
            "subtasks_completed": len(results),
            "result": final_result
        }

    async def _leader_follower_coordination(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """Coordinate using leader-follower pattern."""
        # Find leader
        leader_id = self._select_leader(task)

        if not leader_id:
            return {
                "status": "failed",
                "reason": "No leader available"
            }

        logger.info(f"Leader selected: {leader_id}")

        # Leader plans execution
        leader = self.agents[leader_id]
        plan = await self._leader_create_plan(leader, task)

        # Assign followers
        followers = self._assign_followers(plan, task.required_capabilities)

        # Leader directs execution
        results = await self._leader_direct_execution(leader_id, followers, plan)

        return {
            "status": "success",
            "strategy": "leader_follower",
            "leader": leader_id,
            "followers": followers,
            "results": results
        }

    async def _hierarchical_coordination(
        self,
        task: CoordinatedTask
    ) -> Dict[str, Any]:
        """Coordinate using hierarchical structure."""
        # Organize by role hierarchy
        coordinators = [aid for aid, role in self.agent_roles.items()
                       if role == AgentRole.COORDINATOR]
        specialists = [aid for aid, role in self.agent_roles.items()
                      if role == AgentRole.SPECIALIST]

        if not coordinators:
            return await self._swarm_coordination(task)

        coordinator = self.agents[coordinators[0]]

        # Coordinator delegates to specialists
        delegations = await self._coordinator_delegate(coordinator, task, specialists)

        # Execute hierarchy
        results = await self._execute_hierarchical(delegations)

        return {
            "status": "success",
            "strategy": "hierarchical",
            "coordinator": coordinators[0],
            "delegations": len(delegations),
            "results": results
        }

    async def _collect_proposals(
        self,
        task: CoordinatedTask,
        agent_ids: List[str]
    ) -> List[Dict]:
        """Collect proposals from agents."""
        proposals = []

        for agent_id in agent_ids:
            agent = self.agents[agent_id]

            # Each agent proposes approach
            proposal = {
                "agent_id": agent_id,
                "approach": f"Approach by {agent_id}",
                "estimated_success": 0.8,
                "estimated_duration": 10.0,
                "reasoning": f"Based on past experience with similar tasks"
            }

            proposals.append(proposal)

        return proposals

    async def _vote_on_proposals(
        self,
        proposals: List[Dict],
        agent_ids: List[str]
    ) -> Dict[str, ConsensusVote]:
        """Collect votes on proposals."""
        votes = {}

        for agent_id in agent_ids:
            # Simulate voting - in real system, agents evaluate proposals
            best_proposal = max(proposals, key=lambda p: p["estimated_success"])

            vote = ConsensusVote(
                agent_id=agent_id,
                decision_id="proposal_selection",
                vote="yes" if best_proposal["agent_id"] != agent_id else "abstain",
                confidence=0.85,
                reasoning=f"Highest success probability"
            )

            votes[agent_id] = vote

        return votes

    def _select_by_consensus(
        self,
        proposals: List[Dict],
        votes: Dict[str, ConsensusVote]
    ) -> Dict:
        """Select proposal with strongest consensus."""
        # Count votes per proposal
        vote_counts = {}

        for proposal in proposals:
            yes_votes = sum(1 for v in votes.values()
                          if v.vote == "yes")
            vote_counts[proposal["agent_id"]] = yes_votes

        # Select most voted
        winner_id = max(vote_counts, key=vote_counts.get)
        return next(p for p in proposals if p["agent_id"] == winner_id)

    async def _collect_bids(
        self,
        task: CoordinatedTask,
        agent_ids: List[str]
    ) -> List[AgentBid]:
        """Collect bids from agents."""
        bids = []

        for agent_id in agent_ids:
            agent = self.agents[agent_id]

            # Agent calculates bid
            # In real system, use agent's actual capabilities and stats
            bid = AgentBid(
                agent_id=agent_id,
                task_id=task.task_id,
                confidence=0.8 + (hash(agent_id) % 20) / 100,
                estimated_duration=5.0 + (hash(agent_id) % 10),
                resource_cost=1.0,
                reason=f"Available and capable"
            )

            bids.append(bid)

        return bids

    def _select_winning_bid(
        self,
        bids: List[AgentBid],
        priority: TaskPriority
    ) -> AgentBid:
        """Select winning bid based on task priority."""
        if priority.value >= TaskPriority.HIGH.value:
            # High priority: maximize confidence
            return max(bids, key=lambda b: b.confidence)
        else:
            # Lower priority: balance confidence and cost
            return max(bids, key=lambda b: b.confidence / (b.resource_cost + 0.1))

    def _decompose_task(self, task: CoordinatedTask) -> List[Dict]:
        """Decompose task into subtasks."""
        if task.subtasks:
            return task.subtasks

        # Simple decomposition - in real system, use AI
        return [
            {"id": f"{task.task_id}_1", "description": f"Part 1 of {task.description}"},
            {"id": f"{task.task_id}_2", "description": f"Part 2 of {task.description}"},
        ]

    async def _swarm_self_organize(
        self,
        subtasks: List[Dict],
        agent_ids: List[str]
    ) -> List[Tuple[str, Dict]]:
        """Agents self-organize to handle subtasks."""
        assignments = []

        # Simple round-robin - in real system, agents negotiate
        for i, subtask in enumerate(subtasks):
            agent_id = agent_ids[i % len(agent_ids)]
            assignments.append((agent_id, subtask))

        return assignments

    async def _swarm_execute(
        self,
        assignments: List[Tuple[str, Dict]]
    ) -> List[Dict]:
        """Execute assignments in parallel."""
        tasks = []

        for agent_id, subtask in assignments:
            agent = self.agents[agent_id]
            tasks.append(agent.execute_autonomous(subtask))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def _aggregate_swarm_results(self, results: List) -> Dict:
        """Aggregate results from swarm."""
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0.0,
            "results": successful
        }

    def _select_leader(self, task: CoordinatedTask) -> Optional[str]:
        """Select leader for task."""
        leaders = [aid for aid, role in self.agent_roles.items()
                  if role == AgentRole.LEADER]

        if leaders:
            return leaders[0]

        # Fall back to most experienced agent
        if self.agents:
            return list(self.agents.keys())[0]

        return None

    async def _leader_create_plan(self, leader: Any, task: CoordinatedTask) -> Dict:
        """Leader creates execution plan."""
        return {
            "task_id": task.task_id,
            "steps": self._decompose_task(task),
            "required_roles": task.required_capabilities
        }

    def _assign_followers(
        self,
        plan: Dict,
        required_capabilities: List[str]
    ) -> List[str]:
        """Assign follower agents to plan."""
        followers = []

        for agent_id, agent in self.agents.items():
            if self.agent_roles.get(agent_id) in [AgentRole.SPECIALIST, AgentRole.GENERALIST]:
                # Check capabilities
                if hasattr(agent, 'capabilities'):
                    for cap_name in required_capabilities:
                        if cap_name.lower() in [c.name.lower() for c in agent.capabilities.values()]:
                            followers.append(agent_id)
                            break

        return followers[:5]  # Limit followers

    async def _leader_direct_execution(
        self,
        leader_id: str,
        followers: List[str],
        plan: Dict
    ) -> Dict:
        """Leader directs followers in execution."""
        results = []

        for step in plan["steps"]:
            # Assign step to appropriate follower
            if followers:
                follower_id = followers[len(results) % len(followers)]
                agent = self.agents[follower_id]
                result = await agent.execute_autonomous(step)
                results.append({"agent": follower_id, "result": result})

        return {"steps_completed": len(results), "results": results}

    async def _coordinator_delegate(
        self,
        coordinator: Any,
        task: CoordinatedTask,
        specialists: List[str]
    ) -> List[Tuple[str, Dict]]:
        """Coordinator delegates work to specialists."""
        subtasks = self._decompose_task(task)
        delegations = []

        for i, subtask in enumerate(subtasks):
            if specialists:
                specialist_id = specialists[i % len(specialists)]
                delegations.append((specialist_id, subtask))

        return delegations

    async def _execute_hierarchical(
        self,
        delegations: List[Tuple[str, Dict]]
    ) -> Dict:
        """Execute hierarchical delegations."""
        results = []

        for agent_id, subtask in delegations:
            agent = self.agents[agent_id]
            result = await agent.execute_autonomous(subtask)
            results.append(result)

        return {"delegations_completed": len(results), "results": results}

    async def _execute_distributed(
        self,
        task: CoordinatedTask,
        agent_ids: List[str]
    ) -> List[Dict]:
        """Execute task distributed across agents."""
        subtasks = self._decompose_task(task)

        tasks = []
        for i, subtask in enumerate(subtasks):
            agent_id = agent_ids[i % len(agent_ids)]
            agent = self.agents[agent_id]
            tasks.append(agent.execute_autonomous(subtask))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def _find_capable_agents(self, required_capabilities: List[str]) -> List[str]:
        """Find agents with required capabilities."""
        capable = []

        for agent_id, agent in self.agents.items():
            if not required_capabilities:
                capable.append(agent_id)
                continue

            if hasattr(agent, 'capabilities'):
                for cap_name in required_capabilities:
                    if any(cap_name.lower() in c.name.lower()
                          for c in agent.capabilities.values()):
                        capable.append(agent_id)
                        break

        return capable

    def _record_coordination(self, task: CoordinatedTask, result: Dict):
        """Record coordination event."""
        self.coordination_history.append({
            "task_id": task.task_id,
            "strategy": self.strategy.value,
            "status": result.get("status"),
            "timestamp": datetime.now(),
            "result_summary": {
                k: v for k, v in result.items()
                if k in ["status", "strategy", "agents_used"]
            }
        })

    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        successful = sum(1 for h in self.coordination_history
                        if h["status"] == "success")

        return {
            "total_coordinations": len(self.coordination_history),
            "successful": successful,
            "success_rate": successful / len(self.coordination_history) if self.coordination_history else 0.0,
            "registered_agents": len(self.agents),
            "strategy": self.strategy.value,
            "shared_knowledge_items": len(self.shared_knowledge)
        }
