#!/usr/bin/env python3
"""
BAEL - Coalition Manager
Advanced multi-agent coalition formation and management.

Features:
- Coalition formation
- Coalition stability
- Value distribution
- Power dynamics
- Coalition negotiation
- Coalition dissolution
- Task allocation
- Synergy computation
"""

import asyncio
import copy
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, FrozenSet, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class CoalitionStatus(Enum):
    """Coalition status."""
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"


class MemberRole(Enum):
    """Member roles in coalition."""
    LEADER = "leader"
    MEMBER = "member"
    OBSERVER = "observer"
    CANDIDATE = "candidate"


class VotingRule(Enum):
    """Voting rules."""
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"


class AllocationRule(Enum):
    """Value allocation rules."""
    EQUAL = "equal"
    PROPORTIONAL = "proportional"
    SHAPLEY = "shapley"
    NUCLEOLUS = "nucleolus"
    BARGAINING = "bargaining"


class StabilityType(Enum):
    """Coalition stability types."""
    CORE_STABLE = "core_stable"
    INDIVIDUALLY_RATIONAL = "individually_rational"
    COALITION_RATIONAL = "coalition_rational"
    NASH_STABLE = "nash_stable"


class TaskType(Enum):
    """Task types."""
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    MIXED = "mixed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Agent:
    """Coalition agent."""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    capabilities: Set[str] = field(default_factory=set)
    resources: Dict[str, float] = field(default_factory=dict)
    preferences: Dict[str, float] = field(default_factory=dict)
    power: float = 1.0
    coalitions: List[str] = field(default_factory=list)


@dataclass
class CoalitionMember:
    """Coalition member."""
    agent_id: str
    role: MemberRole = MemberRole.MEMBER
    join_time: datetime = field(default_factory=datetime.now)
    contribution: float = 0.0
    allocation: float = 0.0
    votes: int = 1


@dataclass
class Coalition:
    """Coalition."""
    coalition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    members: Dict[str, CoalitionMember] = field(default_factory=dict)
    status: CoalitionStatus = CoalitionStatus.PROPOSED
    value: float = 0.0
    voting_rule: VotingRule = VotingRule.MAJORITY
    allocation_rule: AllocationRule = AllocationRule.PROPORTIONAL
    objectives: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoalitionProposal:
    """Coalition proposal."""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposer_id: str = ""
    proposed_members: Set[str] = field(default_factory=set)
    proposed_value: float = 0.0
    allocation_proposal: Dict[str, float] = field(default_factory=dict)
    votes_for: Set[str] = field(default_factory=set)
    votes_against: Set[str] = field(default_factory=set)
    deadline: Optional[datetime] = None
    status: str = "pending"


@dataclass
class Task:
    """Coalition task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_type: TaskType = TaskType.COOPERATIVE
    required_capabilities: Set[str] = field(default_factory=set)
    required_resources: Dict[str, float] = field(default_factory=dict)
    value: float = 0.0
    assigned_coalition: Optional[str] = None
    assigned_agents: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class CoalitionStats:
    """Coalition manager statistics."""
    total_coalitions: int = 0
    active_coalitions: int = 0
    total_agents: int = 0
    proposals_made: int = 0
    proposals_accepted: int = 0
    tasks_completed: int = 0


# =============================================================================
# VALUE FUNCTION
# =============================================================================

class ValueFunction(ABC):
    """Abstract value function for coalitions."""

    @abstractmethod
    def compute(
        self,
        coalition_members: Set[str],
        agents: Dict[str, Agent]
    ) -> float:
        """Compute coalition value."""
        pass


class AdditiveValueFunction(ValueFunction):
    """Additive value function."""

    def compute(
        self,
        coalition_members: Set[str],
        agents: Dict[str, Agent]
    ) -> float:
        total = 0.0
        for agent_id in coalition_members:
            if agent_id in agents:
                agent = agents[agent_id]
                total += agent.power * sum(agent.resources.values())
        return total


class SynergyValueFunction(ValueFunction):
    """Value function with synergies."""

    def __init__(self, synergy_bonus: float = 0.1):
        self._synergy_bonus = synergy_bonus

    def compute(
        self,
        coalition_members: Set[str],
        agents: Dict[str, Agent]
    ) -> float:
        # Base value
        base_value = 0.0
        capabilities = set()

        for agent_id in coalition_members:
            if agent_id in agents:
                agent = agents[agent_id]
                base_value += agent.power * sum(agent.resources.values())
                capabilities.update(agent.capabilities)

        # Synergy bonus for capability diversity
        synergy = len(capabilities) * self._synergy_bonus * base_value

        # Size bonus (larger coalitions can tackle bigger tasks)
        size_bonus = math.log(len(coalition_members) + 1) * base_value * 0.1

        return base_value + synergy + size_bonus


class TaskBasedValueFunction(ValueFunction):
    """Value based on accomplishable tasks."""

    def __init__(self, tasks: List[Task]):
        self._tasks = tasks

    def compute(
        self,
        coalition_members: Set[str],
        agents: Dict[str, Agent]
    ) -> float:
        # Compute combined capabilities and resources
        combined_caps = set()
        combined_resources: Dict[str, float] = defaultdict(float)

        for agent_id in coalition_members:
            if agent_id in agents:
                agent = agents[agent_id]
                combined_caps.update(agent.capabilities)
                for res, val in agent.resources.items():
                    combined_resources[res] += val

        # Sum value of accomplishable tasks
        value = 0.0
        for task in self._tasks:
            if task.completed:
                continue

            # Check capability requirements
            if not task.required_capabilities.issubset(combined_caps):
                continue

            # Check resource requirements
            can_do = True
            for res, req in task.required_resources.items():
                if combined_resources.get(res, 0) < req:
                    can_do = False
                    break

            if can_do:
                value += task.value

        return value


# =============================================================================
# ALLOCATION CALCULATOR
# =============================================================================

class AllocationCalculator:
    """Calculate value allocations."""

    def __init__(self, value_function: ValueFunction):
        self._value_function = value_function

    def compute_equal(
        self,
        coalition: Coalition,
        agents: Dict[str, Agent]
    ) -> Dict[str, float]:
        """Equal allocation."""
        n = len(coalition.members)
        if n == 0:
            return {}

        share = coalition.value / n
        return {mid: share for mid in coalition.members}

    def compute_proportional(
        self,
        coalition: Coalition,
        agents: Dict[str, Agent]
    ) -> Dict[str, float]:
        """Proportional allocation based on contribution."""
        total_contribution = sum(m.contribution for m in coalition.members.values())

        if total_contribution == 0:
            return self.compute_equal(coalition, agents)

        allocations = {}
        for mid, member in coalition.members.items():
            allocations[mid] = coalition.value * (member.contribution / total_contribution)

        return allocations

    def compute_shapley(
        self,
        coalition: Coalition,
        agents: Dict[str, Agent]
    ) -> Dict[str, float]:
        """Shapley value allocation."""
        members = set(coalition.members.keys())
        n = len(members)

        if n == 0:
            return {}

        shapley_values = {mid: 0.0 for mid in members}

        # For each possible ordering (approximate for large coalitions)
        max_samples = min(math.factorial(n), 1000)
        member_list = list(members)

        for _ in range(max_samples):
            random.shuffle(member_list)

            current_coalition: Set[str] = set()
            prev_value = 0.0

            for agent_id in member_list:
                current_coalition.add(agent_id)
                new_value = self._value_function.compute(current_coalition, agents)
                marginal = new_value - prev_value
                shapley_values[agent_id] += marginal
                prev_value = new_value

        # Average
        for mid in shapley_values:
            shapley_values[mid] /= max_samples

        return shapley_values

    def allocate(
        self,
        coalition: Coalition,
        agents: Dict[str, Agent],
        rule: AllocationRule
    ) -> Dict[str, float]:
        """Compute allocation based on rule."""
        if rule == AllocationRule.EQUAL:
            return self.compute_equal(coalition, agents)
        elif rule == AllocationRule.PROPORTIONAL:
            return self.compute_proportional(coalition, agents)
        elif rule == AllocationRule.SHAPLEY:
            return self.compute_shapley(coalition, agents)
        else:
            return self.compute_proportional(coalition, agents)


# =============================================================================
# STABILITY CHECKER
# =============================================================================

class StabilityChecker:
    """Check coalition stability."""

    def __init__(
        self,
        value_function: ValueFunction,
        agents: Dict[str, Agent]
    ):
        self._value_function = value_function
        self._agents = agents

    def is_individually_rational(
        self,
        coalition: Coalition,
        allocations: Dict[str, float]
    ) -> Tuple[bool, List[str]]:
        """Check if individually rational (no one worse off alone)."""
        violators = []

        for agent_id, allocation in allocations.items():
            # Value alone
            alone_value = self._value_function.compute({agent_id}, self._agents)

            if allocation < alone_value:
                violators.append(agent_id)

        return len(violators) == 0, violators

    def is_core_stable(
        self,
        coalition: Coalition,
        allocations: Dict[str, float]
    ) -> Tuple[bool, Optional[Set[str]]]:
        """Check if in core (no blocking coalition)."""
        members = set(coalition.members.keys())

        # Check all possible subcoalitions
        for size in range(1, len(members)):
            for subset in self._subsets(members, size):
                subset_value = self._value_function.compute(subset, self._agents)
                subset_allocation = sum(allocations.get(a, 0) for a in subset)

                if subset_value > subset_allocation:
                    return False, subset

        return True, None

    def _subsets(
        self,
        s: Set[str],
        size: int
    ) -> List[Set[str]]:
        """Generate subsets of given size."""
        from itertools import combinations
        return [set(c) for c in combinations(s, size)]

    def check_stability(
        self,
        coalition: Coalition,
        allocations: Dict[str, float],
        stability_type: StabilityType
    ) -> Tuple[bool, str]:
        """Check stability of given type."""
        if stability_type == StabilityType.INDIVIDUALLY_RATIONAL:
            stable, violators = self.is_individually_rational(coalition, allocations)
            msg = "Stable" if stable else f"Violators: {violators}"
            return stable, msg

        elif stability_type == StabilityType.CORE_STABLE:
            stable, blocking = self.is_core_stable(coalition, allocations)
            msg = "In core" if stable else f"Blocking coalition: {blocking}"
            return stable, msg

        return True, "Unknown stability type"


# =============================================================================
# VOTING SYSTEM
# =============================================================================

class VotingSystem:
    """Coalition voting system."""

    def __init__(self, rule: VotingRule = VotingRule.MAJORITY):
        self._rule = rule

    def evaluate(
        self,
        proposal: CoalitionProposal,
        members: Dict[str, CoalitionMember]
    ) -> Tuple[bool, str]:
        """Evaluate proposal based on votes."""
        total_votes = sum(m.votes for m in members.values())
        votes_for = sum(
            members[a].votes for a in proposal.votes_for
            if a in members
        )
        votes_against = sum(
            members[a].votes for a in proposal.votes_against
            if a in members
        )

        if self._rule == VotingRule.MAJORITY:
            threshold = total_votes / 2
            passed = votes_for > threshold

        elif self._rule == VotingRule.SUPERMAJORITY:
            threshold = total_votes * 2 / 3
            passed = votes_for >= threshold

        elif self._rule == VotingRule.UNANIMOUS:
            passed = votes_against == 0 and votes_for == total_votes

        elif self._rule == VotingRule.WEIGHTED:
            passed = votes_for > votes_against

        else:
            passed = votes_for > votes_against

        msg = f"For: {votes_for}, Against: {votes_against}, Total: {total_votes}"
        return passed, msg


# =============================================================================
# TASK ALLOCATOR
# =============================================================================

class TaskAllocator:
    """Allocate tasks to coalition members."""

    def __init__(self):
        pass

    def allocate(
        self,
        task: Task,
        coalition: Coalition,
        agents: Dict[str, Agent]
    ) -> List[str]:
        """Allocate task to agents in coalition."""
        # Find agents that can contribute to task
        candidates = []

        for agent_id in coalition.members:
            if agent_id not in agents:
                continue

            agent = agents[agent_id]

            # Check capability match
            cap_match = len(agent.capabilities & task.required_capabilities)

            # Check resource availability
            res_match = sum(
                min(agent.resources.get(r, 0), req)
                for r, req in task.required_resources.items()
            )

            if cap_match > 0 or res_match > 0:
                candidates.append((agent_id, cap_match + res_match))

        # Sort by contribution potential
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Select agents
        selected = []
        remaining_caps = set(task.required_capabilities)
        remaining_resources = dict(task.required_resources)

        for agent_id, _ in candidates:
            agent = agents[agent_id]

            # Check if agent adds value
            adds_caps = agent.capabilities & remaining_caps
            adds_resources = False

            for r, req in remaining_resources.items():
                if req > 0 and agent.resources.get(r, 0) > 0:
                    adds_resources = True
                    break

            if adds_caps or adds_resources:
                selected.append(agent_id)
                remaining_caps -= agent.capabilities

                for r in remaining_resources:
                    remaining_resources[r] -= agent.resources.get(r, 0)

        return selected


# =============================================================================
# COALITION MANAGER
# =============================================================================

class CoalitionManager:
    """
    Coalition Manager for BAEL.

    Advanced multi-agent coalition formation and management.
    """

    def __init__(
        self,
        value_function: Optional[ValueFunction] = None
    ):
        self._value_function = value_function or SynergyValueFunction()
        self._allocation_calculator = AllocationCalculator(self._value_function)
        self._voting_system = VotingSystem()
        self._task_allocator = TaskAllocator()

        self._agents: Dict[str, Agent] = {}
        self._coalitions: Dict[str, Coalition] = {}
        self._proposals: Dict[str, CoalitionProposal] = {}
        self._tasks: Dict[str, Task] = {}
        self._stats = CoalitionStats()

    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        name: str,
        capabilities: Optional[Set[str]] = None,
        resources: Optional[Dict[str, float]] = None,
        power: float = 1.0
    ) -> Agent:
        """Register new agent."""
        agent = Agent(
            name=name,
            capabilities=capabilities or set(),
            resources=resources or {},
            power=power
        )

        self._agents[agent.agent_id] = agent
        self._stats.total_agents += 1

        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        """List all agents."""
        return list(self._agents.values())

    # -------------------------------------------------------------------------
    # COALITION FORMATION
    # -------------------------------------------------------------------------

    def create_coalition(
        self,
        name: str,
        initial_members: Optional[List[str]] = None,
        objectives: Optional[List[str]] = None,
        voting_rule: VotingRule = VotingRule.MAJORITY,
        allocation_rule: AllocationRule = AllocationRule.PROPORTIONAL
    ) -> Coalition:
        """Create new coalition."""
        coalition = Coalition(
            name=name,
            objectives=objectives or [],
            voting_rule=voting_rule,
            allocation_rule=allocation_rule
        )

        # Add initial members
        if initial_members:
            for i, agent_id in enumerate(initial_members):
                role = MemberRole.LEADER if i == 0 else MemberRole.MEMBER
                coalition.members[agent_id] = CoalitionMember(
                    agent_id=agent_id,
                    role=role
                )

                # Update agent
                if agent_id in self._agents:
                    self._agents[agent_id].coalitions.append(coalition.coalition_id)

        # Compute initial value
        member_set = set(coalition.members.keys())
        coalition.value = self._value_function.compute(member_set, self._agents)
        coalition.status = CoalitionStatus.ACTIVE

        self._coalitions[coalition.coalition_id] = coalition
        self._stats.total_coalitions += 1
        self._stats.active_coalitions += 1

        return coalition

    def get_coalition(self, coalition_id: str) -> Optional[Coalition]:
        """Get coalition by ID."""
        return self._coalitions.get(coalition_id)

    def list_coalitions(
        self,
        status: Optional[CoalitionStatus] = None
    ) -> List[Coalition]:
        """List coalitions."""
        coalitions = list(self._coalitions.values())
        if status:
            coalitions = [c for c in coalitions if c.status == status]
        return coalitions

    # -------------------------------------------------------------------------
    # MEMBERSHIP MANAGEMENT
    # -------------------------------------------------------------------------

    def add_member(
        self,
        coalition_id: str,
        agent_id: str,
        role: MemberRole = MemberRole.MEMBER
    ) -> bool:
        """Add member to coalition."""
        coalition = self._coalitions.get(coalition_id)
        agent = self._agents.get(agent_id)

        if not coalition or not agent:
            return False

        if agent_id in coalition.members:
            return False

        coalition.members[agent_id] = CoalitionMember(
            agent_id=agent_id,
            role=role
        )

        agent.coalitions.append(coalition_id)

        # Recompute value
        member_set = set(coalition.members.keys())
        coalition.value = self._value_function.compute(member_set, self._agents)

        return True

    def remove_member(
        self,
        coalition_id: str,
        agent_id: str
    ) -> bool:
        """Remove member from coalition."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition or agent_id not in coalition.members:
            return False

        del coalition.members[agent_id]

        if agent_id in self._agents:
            agent = self._agents[agent_id]
            if coalition_id in agent.coalitions:
                agent.coalitions.remove(coalition_id)

        # Recompute value
        if coalition.members:
            member_set = set(coalition.members.keys())
            coalition.value = self._value_function.compute(member_set, self._agents)
        else:
            coalition.value = 0
            coalition.status = CoalitionStatus.DISSOLVED
            self._stats.active_coalitions -= 1

        return True

    def change_role(
        self,
        coalition_id: str,
        agent_id: str,
        new_role: MemberRole
    ) -> bool:
        """Change member role."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition or agent_id not in coalition.members:
            return False

        coalition.members[agent_id].role = new_role
        return True

    # -------------------------------------------------------------------------
    # PROPOSALS AND VOTING
    # -------------------------------------------------------------------------

    def create_proposal(
        self,
        proposer_id: str,
        proposed_members: Set[str],
        allocation_proposal: Optional[Dict[str, float]] = None,
        deadline_hours: float = 24.0
    ) -> CoalitionProposal:
        """Create coalition proposal."""
        # Compute proposed value
        proposed_value = self._value_function.compute(proposed_members, self._agents)

        # Default allocation
        if allocation_proposal is None:
            allocation_proposal = {
                m: proposed_value / len(proposed_members)
                for m in proposed_members
            }

        proposal = CoalitionProposal(
            proposer_id=proposer_id,
            proposed_members=proposed_members,
            proposed_value=proposed_value,
            allocation_proposal=allocation_proposal,
            deadline=datetime.now() + timedelta(hours=deadline_hours)
        )

        # Proposer votes for
        proposal.votes_for.add(proposer_id)

        self._proposals[proposal.proposal_id] = proposal
        self._stats.proposals_made += 1

        return proposal

    def vote(
        self,
        proposal_id: str,
        agent_id: str,
        in_favor: bool
    ) -> bool:
        """Vote on proposal."""
        proposal = self._proposals.get(proposal_id)

        if not proposal or proposal.status != "pending":
            return False

        if agent_id not in proposal.proposed_members:
            return False

        # Remove previous vote
        proposal.votes_for.discard(agent_id)
        proposal.votes_against.discard(agent_id)

        if in_favor:
            proposal.votes_for.add(agent_id)
        else:
            proposal.votes_against.add(agent_id)

        return True

    def evaluate_proposal(
        self,
        proposal_id: str
    ) -> Tuple[bool, str, Optional[Coalition]]:
        """Evaluate proposal and possibly create coalition."""
        proposal = self._proposals.get(proposal_id)

        if not proposal:
            return False, "Proposal not found", None

        # Check deadline
        if proposal.deadline and datetime.now() > proposal.deadline:
            proposal.status = "expired"
            return False, "Proposal expired", None

        # Check if all members have voted
        all_voted = proposal.votes_for | proposal.votes_against == proposal.proposed_members

        # Create temporary member dict for voting
        temp_members = {
            m: CoalitionMember(agent_id=m)
            for m in proposal.proposed_members
        }

        passed, msg = self._voting_system.evaluate(proposal, temp_members)

        if passed:
            proposal.status = "accepted"
            self._stats.proposals_accepted += 1

            # Create coalition
            coalition = self.create_coalition(
                name=f"Coalition_{proposal.proposal_id[:8]}",
                initial_members=list(proposal.proposed_members)
            )

            # Apply allocation
            for agent_id, allocation in proposal.allocation_proposal.items():
                if agent_id in coalition.members:
                    coalition.members[agent_id].allocation = allocation

            return True, msg, coalition

        elif all_voted:
            proposal.status = "rejected"

        return False, msg, None

    # -------------------------------------------------------------------------
    # VALUE ALLOCATION
    # -------------------------------------------------------------------------

    def compute_allocations(
        self,
        coalition_id: str,
        rule: Optional[AllocationRule] = None
    ) -> Dict[str, float]:
        """Compute value allocations."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition:
            return {}

        rule = rule or coalition.allocation_rule
        allocations = self._allocation_calculator.allocate(
            coalition,
            self._agents,
            rule
        )

        # Update members
        for agent_id, allocation in allocations.items():
            if agent_id in coalition.members:
                coalition.members[agent_id].allocation = allocation

        return allocations

    def update_contributions(
        self,
        coalition_id: str,
        contributions: Dict[str, float]
    ) -> bool:
        """Update member contributions."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition:
            return False

        for agent_id, contribution in contributions.items():
            if agent_id in coalition.members:
                coalition.members[agent_id].contribution = contribution

        return True

    # -------------------------------------------------------------------------
    # STABILITY ANALYSIS
    # -------------------------------------------------------------------------

    def check_stability(
        self,
        coalition_id: str,
        stability_type: StabilityType = StabilityType.INDIVIDUALLY_RATIONAL
    ) -> Tuple[bool, str]:
        """Check coalition stability."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition:
            return False, "Coalition not found"

        allocations = {
            m.agent_id: m.allocation
            for m in coalition.members.values()
        }

        checker = StabilityChecker(self._value_function, self._agents)
        return checker.check_stability(coalition, allocations, stability_type)

    def find_blocking_coalitions(
        self,
        coalition_id: str
    ) -> List[Set[str]]:
        """Find potential blocking coalitions."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition:
            return []

        allocations = {
            m.agent_id: m.allocation
            for m in coalition.members.values()
        }

        members = set(coalition.members.keys())
        blocking = []

        for size in range(2, len(members)):
            for subset in self._subsets(members, size):
                subset_value = self._value_function.compute(subset, self._agents)
                subset_allocation = sum(allocations.get(a, 0) for a in subset)

                if subset_value > subset_allocation * 1.1:  # 10% improvement threshold
                    blocking.append(subset)

        return blocking

    def _subsets(
        self,
        s: Set[str],
        size: int
    ) -> List[Set[str]]:
        """Generate subsets of given size."""
        from itertools import combinations
        return [set(c) for c in combinations(s, size)]

    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------

    def create_task(
        self,
        name: str,
        task_type: TaskType = TaskType.COOPERATIVE,
        required_capabilities: Optional[Set[str]] = None,
        required_resources: Optional[Dict[str, float]] = None,
        value: float = 10.0
    ) -> Task:
        """Create task."""
        task = Task(
            name=name,
            task_type=task_type,
            required_capabilities=required_capabilities or set(),
            required_resources=required_resources or {},
            value=value
        )

        self._tasks[task.task_id] = task
        return task

    def assign_task(
        self,
        task_id: str,
        coalition_id: str
    ) -> List[str]:
        """Assign task to coalition."""
        task = self._tasks.get(task_id)
        coalition = self._coalitions.get(coalition_id)

        if not task or not coalition:
            return []

        assigned = self._task_allocator.allocate(task, coalition, self._agents)

        task.assigned_coalition = coalition_id
        task.assigned_agents = assigned

        return assigned

    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed."""
        task = self._tasks.get(task_id)

        if not task:
            return False

        task.completed = True
        self._stats.tasks_completed += 1

        # Distribute value to assigned agents
        if task.assigned_agents and task.assigned_coalition:
            coalition = self._coalitions.get(task.assigned_coalition)
            if coalition:
                share = task.value / len(task.assigned_agents)
                for agent_id in task.assigned_agents:
                    if agent_id in coalition.members:
                        coalition.members[agent_id].contribution += share

        return True

    # -------------------------------------------------------------------------
    # COALITION LIFECYCLE
    # -------------------------------------------------------------------------

    def dissolve_coalition(self, coalition_id: str) -> bool:
        """Dissolve coalition."""
        coalition = self._coalitions.get(coalition_id)

        if not coalition:
            return False

        coalition.status = CoalitionStatus.DISSOLVING

        # Remove from agents
        for agent_id in coalition.members:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                if coalition_id in agent.coalitions:
                    agent.coalitions.remove(coalition_id)

        coalition.members.clear()
        coalition.status = CoalitionStatus.DISSOLVED
        self._stats.active_coalitions -= 1

        return True

    def merge_coalitions(
        self,
        coalition_ids: List[str],
        new_name: str
    ) -> Optional[Coalition]:
        """Merge multiple coalitions."""
        coalitions = [
            self._coalitions.get(cid)
            for cid in coalition_ids
        ]

        if None in coalitions:
            return None

        # Gather all members
        all_members = []
        for coalition in coalitions:
            all_members.extend(coalition.members.keys())

        # Create new coalition
        new_coalition = self.create_coalition(
            name=new_name,
            initial_members=all_members
        )

        # Dissolve old coalitions
        for cid in coalition_ids:
            self.dissolve_coalition(cid)

        return new_coalition

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def compute_coalition_value(
        self,
        member_ids: Set[str]
    ) -> float:
        """Compute potential coalition value."""
        return self._value_function.compute(member_ids, self._agents)

    def find_optimal_coalition(
        self,
        agent_ids: Set[str],
        min_size: int = 2
    ) -> Tuple[Set[str], float]:
        """Find optimal coalition among agents."""
        if len(agent_ids) < min_size:
            return set(), 0.0

        best_coalition: Set[str] = set()
        best_value = 0.0

        from itertools import combinations

        for size in range(min_size, len(agent_ids) + 1):
            for subset in combinations(agent_ids, size):
                subset_set = set(subset)
                value = self._value_function.compute(subset_set, self._agents)

                if value > best_value:
                    best_value = value
                    best_coalition = subset_set

        return best_coalition, best_value

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CoalitionStats:
        """Get manager statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Coalition Manager."""
    print("=" * 70)
    print("BAEL - COALITION MANAGER DEMO")
    print("Advanced Multi-Agent Coalition Formation and Management")
    print("=" * 70)
    print()

    manager = CoalitionManager()

    # 1. Register Agents
    print("1. REGISTER AGENTS:")
    print("-" * 40)

    alice = manager.register_agent(
        "Alice",
        capabilities={"coding", "design"},
        resources={"compute": 10, "memory": 5},
        power=1.2
    )

    bob = manager.register_agent(
        "Bob",
        capabilities={"coding", "testing"},
        resources={"compute": 8, "memory": 4},
        power=1.0
    )

    charlie = manager.register_agent(
        "Charlie",
        capabilities={"design", "marketing"},
        resources={"creativity": 10, "budget": 20},
        power=0.9
    )

    diana = manager.register_agent(
        "Diana",
        capabilities={"management", "marketing"},
        resources={"budget": 30, "network": 15},
        power=1.5
    )

    for agent in manager.list_agents():
        print(f"   {agent.name}: caps={agent.capabilities}, power={agent.power}")
    print()

    # 2. Create Coalition
    print("2. CREATE COALITION:")
    print("-" * 40)

    coalition = manager.create_coalition(
        name="Project Alpha",
        initial_members=[alice.agent_id, bob.agent_id],
        objectives=["Build product", "Launch market"],
        allocation_rule=AllocationRule.SHAPLEY
    )

    print(f"   Created: {coalition.name}")
    print(f"   Members: {len(coalition.members)}")
    print(f"   Value: {coalition.value:.2f}")
    print()

    # 3. Add Members
    print("3. ADD MEMBERS:")
    print("-" * 40)

    manager.add_member(coalition.coalition_id, charlie.agent_id)
    coalition = manager.get_coalition(coalition.coalition_id)

    print(f"   Added Charlie to coalition")
    print(f"   New value: {coalition.value:.2f}")
    print()

    # 4. Compute Allocations
    print("4. COMPUTE ALLOCATIONS:")
    print("-" * 40)

    # Set contributions
    manager.update_contributions(coalition.coalition_id, {
        alice.agent_id: 10,
        bob.agent_id: 8,
        charlie.agent_id: 6,
    })

    # Shapley allocation
    allocations = manager.compute_allocations(
        coalition.coalition_id,
        AllocationRule.SHAPLEY
    )

    for agent_id, allocation in allocations.items():
        agent = manager.get_agent(agent_id)
        print(f"   {agent.name}: {allocation:.2f}")
    print()

    # 5. Check Stability
    print("5. CHECK STABILITY:")
    print("-" * 40)

    stable, msg = manager.check_stability(
        coalition.coalition_id,
        StabilityType.INDIVIDUALLY_RATIONAL
    )
    print(f"   Individually rational: {stable}")
    print(f"   {msg}")

    stable, msg = manager.check_stability(
        coalition.coalition_id,
        StabilityType.CORE_STABLE
    )
    print(f"   Core stable: {stable}")
    print()

    # 6. Create Proposal
    print("6. CREATE PROPOSAL:")
    print("-" * 40)

    proposal = manager.create_proposal(
        diana.agent_id,
        proposed_members={diana.agent_id, charlie.agent_id, bob.agent_id},
        deadline_hours=24
    )

    print(f"   Proposal: {proposal.proposal_id[:8]}...")
    print(f"   Proposed value: {proposal.proposed_value:.2f}")
    print()

    # 7. Vote on Proposal
    print("7. VOTE ON PROPOSAL:")
    print("-" * 40)

    manager.vote(proposal.proposal_id, charlie.agent_id, True)
    manager.vote(proposal.proposal_id, bob.agent_id, True)

    print(f"   Charlie voted: YES")
    print(f"   Bob voted: YES")
    print(f"   Votes for: {len(proposal.votes_for)}")
    print()

    # 8. Evaluate Proposal
    print("8. EVALUATE PROPOSAL:")
    print("-" * 40)

    passed, msg, new_coalition = manager.evaluate_proposal(proposal.proposal_id)
    print(f"   Passed: {passed}")
    print(f"   {msg}")
    if new_coalition:
        print(f"   New coalition: {new_coalition.name}")
    print()

    # 9. Create Task
    print("9. CREATE TASK:")
    print("-" * 40)

    task = manager.create_task(
        name="Build MVP",
        task_type=TaskType.COOPERATIVE,
        required_capabilities={"coding", "design"},
        required_resources={"compute": 5, "memory": 3},
        value=50.0
    )

    print(f"   Task: {task.name}")
    print(f"   Required: {task.required_capabilities}")
    print(f"   Value: {task.value}")
    print()

    # 10. Assign Task
    print("10. ASSIGN TASK:")
    print("-" * 40)

    assigned = manager.assign_task(task.task_id, coalition.coalition_id)

    print(f"   Assigned to:")
    for agent_id in assigned:
        agent = manager.get_agent(agent_id)
        print(f"     - {agent.name}")
    print()

    # 11. Complete Task
    print("11. COMPLETE TASK:")
    print("-" * 40)

    manager.complete_task(task.task_id)

    print(f"   Task completed!")

    # Show updated contributions
    coalition = manager.get_coalition(coalition.coalition_id)
    for member in coalition.members.values():
        agent = manager.get_agent(member.agent_id)
        print(f"   {agent.name} contribution: {member.contribution:.2f}")
    print()

    # 12. Find Optimal Coalition
    print("12. FIND OPTIMAL COALITION:")
    print("-" * 40)

    all_agents = {a.agent_id for a in manager.list_agents()}
    optimal, value = manager.find_optimal_coalition(all_agents, min_size=2)

    print(f"   Optimal coalition value: {value:.2f}")
    print(f"   Members:")
    for agent_id in optimal:
        agent = manager.get_agent(agent_id)
        print(f"     - {agent.name}")
    print()

    # 13. Merge Coalitions
    print("13. MERGE COALITIONS:")
    print("-" * 40)

    if new_coalition:
        merged = manager.merge_coalitions(
            [coalition.coalition_id, new_coalition.coalition_id],
            "Super Coalition"
        )

        if merged:
            print(f"   Created: {merged.name}")
            print(f"   Members: {len(merged.members)}")
            print(f"   Value: {merged.value:.2f}")
    print()

    # 14. List Coalitions
    print("14. LIST COALITIONS:")
    print("-" * 40)

    for c in manager.list_coalitions():
        print(f"   {c.name}: {c.status.value}, members={len(c.members)}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total coalitions: {stats.total_coalitions}")
    print(f"   Active coalitions: {stats.active_coalitions}")
    print(f"   Total agents: {stats.total_agents}")
    print(f"   Proposals made: {stats.proposals_made}")
    print(f"   Proposals accepted: {stats.proposals_accepted}")
    print(f"   Tasks completed: {stats.tasks_completed}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Coalition Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
