#!/usr/bin/env python3
"""
BAEL - Collaboration Engine
Multi-agent collaboration and teamwork.

Features:
- Team formation
- Role assignment
- Collaborative tasks
- Shared knowledge
- Synergy management
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TeamStatus(Enum):
    """Team status."""
    FORMING = "forming"
    ACTIVE = "active"
    WORKING = "working"
    PAUSED = "paused"
    DISBANDED = "disbanded"


class RoleType(Enum):
    """Role types."""
    LEADER = "leader"
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


class CollaborationType(Enum):
    """Collaboration types."""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    PIPELINE = "pipeline"
    COMPETITIVE = "competitive"
    COOPERATIVE = "cooperative"


class TaskAllocation(Enum):
    """Task allocation strategies."""
    ROUND_ROBIN = "round_robin"
    CAPABILITY = "capability"
    LOAD_BALANCE = "load_balance"
    VOLUNTEER = "volunteer"
    AUCTION = "auction"


class ContributionType(Enum):
    """Contribution types."""
    TASK_COMPLETE = "task_complete"
    KNOWLEDGE_SHARE = "knowledge_share"
    ASSISTANCE = "assistance"
    REVIEW = "review"
    COORDINATION = "coordination"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AgentCapability:
    """Agent capability definition."""
    capability_id: str = ""
    name: str = ""
    skill_level: float = 0.5
    domains: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.capability_id:
            self.capability_id = str(uuid.uuid4())[:8]


@dataclass
class Role:
    """A role in a team."""
    role_id: str = ""
    name: str = ""
    role_type: RoleType = RoleType.EXECUTOR
    required_capabilities: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    max_assignments: int = 1
    current_assignments: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.role_id:
            self.role_id = str(uuid.uuid4())[:8]


@dataclass
class TeamMember:
    """A team member."""
    agent_id: str = ""
    name: str = ""
    roles: Set[str] = field(default_factory=set)
    capabilities: List[AgentCapability] = field(default_factory=list)
    workload: float = 0.0
    availability: float = 1.0
    joined_at: datetime = field(default_factory=datetime.now)
    contribution_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Team:
    """A collaboration team."""
    team_id: str = ""
    name: str = ""
    status: TeamStatus = TeamStatus.FORMING
    leader_id: Optional[str] = None
    members: Dict[str, TeamMember] = field(default_factory=dict)
    roles: Dict[str, Role] = field(default_factory=dict)
    goal: str = ""
    collab_type: CollaborationType = CollaborationType.COOPERATIVE
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.team_id:
            self.team_id = str(uuid.uuid4())[:8]


@dataclass
class CollaborativeTask:
    """A collaborative task."""
    task_id: str = ""
    name: str = ""
    description: str = ""
    team_id: str = ""
    assigned_to: Set[str] = field(default_factory=set)
    required_capabilities: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    status: str = "pending"
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]


@dataclass
class Contribution:
    """A contribution record."""
    contribution_id: str = ""
    agent_id: str = ""
    team_id: str = ""
    contribution_type: ContributionType = ContributionType.TASK_COMPLETE
    task_id: Optional[str] = None
    value: float = 1.0
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.contribution_id:
            self.contribution_id = str(uuid.uuid4())[:8]


@dataclass
class SharedKnowledge:
    """Shared knowledge item."""
    knowledge_id: str = ""
    team_id: str = ""
    contributor_id: str = ""
    content: Any = None
    knowledge_type: str = "general"
    tags: Set[str] = field(default_factory=set)
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.knowledge_id:
            self.knowledge_id = str(uuid.uuid4())[:8]


@dataclass
class CollaborationStats:
    """Collaboration statistics."""
    teams_formed: int = 0
    tasks_completed: int = 0
    knowledge_shared: int = 0
    total_contributions: int = 0
    avg_team_size: float = 0.0
    synergy_score: float = 0.0


# =============================================================================
# CAPABILITY MANAGER
# =============================================================================

class CapabilityManager:
    """Manage agent capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, AgentCapability] = {}
        self._by_agent: Dict[str, Set[str]] = defaultdict(set)
        self._by_domain: Dict[str, Set[str]] = defaultdict(set)

    def register(
        self,
        agent_id: str,
        name: str,
        skill_level: float = 0.5,
        domains: Optional[Set[str]] = None
    ) -> AgentCapability:
        """Register a capability."""
        capability = AgentCapability(
            name=name,
            skill_level=skill_level,
            domains=domains or set()
        )

        self._capabilities[capability.capability_id] = capability
        self._by_agent[agent_id].add(capability.capability_id)

        for domain in capability.domains:
            self._by_domain[domain].add(capability.capability_id)

        return capability

    def get(self, capability_id: str) -> Optional[AgentCapability]:
        """Get a capability."""
        return self._capabilities.get(capability_id)

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Get capabilities for an agent."""
        cap_ids = self._by_agent.get(agent_id, set())
        return [self._capabilities[cid] for cid in cap_ids if cid in self._capabilities]

    def find_by_domain(self, domain: str) -> List[AgentCapability]:
        """Find capabilities by domain."""
        cap_ids = self._by_domain.get(domain, set())
        return [self._capabilities[cid] for cid in cap_ids if cid in self._capabilities]

    def match_requirements(
        self,
        agent_id: str,
        required_capabilities: List[str]
    ) -> float:
        """Calculate how well an agent matches capability requirements."""
        if not required_capabilities:
            return 1.0

        agent_caps = self.get_agent_capabilities(agent_id)
        agent_cap_names = {cap.name for cap in agent_caps}

        matched = 0
        total_skill = 0.0

        for req in required_capabilities:
            if req in agent_cap_names:
                matched += 1
                for cap in agent_caps:
                    if cap.name == req:
                        total_skill += cap.skill_level
                        break

        if matched == 0:
            return 0.0

        coverage = matched / len(required_capabilities)
        avg_skill = total_skill / matched

        return coverage * avg_skill


# =============================================================================
# ROLE MANAGER
# =============================================================================

class RoleManager:
    """Manage team roles."""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._assignments: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    def define_role(
        self,
        name: str,
        role_type: RoleType = RoleType.EXECUTOR,
        required_capabilities: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None,
        max_assignments: int = 1
    ) -> Role:
        """Define a role."""
        role = Role(
            name=name,
            role_type=role_type,
            required_capabilities=required_capabilities or [],
            permissions=permissions or set(),
            max_assignments=max_assignments
        )

        self._roles[role.role_id] = role

        return role

    def assign_role(
        self,
        team_id: str,
        agent_id: str,
        role_id: str
    ) -> bool:
        """Assign a role to an agent."""
        role = self._roles.get(role_id)
        if not role:
            return False

        current = len(self._assignments[team_id][role_id])
        if current >= role.max_assignments:
            return False

        self._assignments[team_id][role_id].add(agent_id)
        role.current_assignments += 1

        return True

    def unassign_role(
        self,
        team_id: str,
        agent_id: str,
        role_id: str
    ) -> bool:
        """Unassign a role from an agent."""
        role = self._roles.get(role_id)
        if not role:
            return False

        if agent_id in self._assignments[team_id][role_id]:
            self._assignments[team_id][role_id].discard(agent_id)
            role.current_assignments = max(0, role.current_assignments - 1)
            return True

        return False

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role."""
        return self._roles.get(role_id)

    def get_agent_roles(self, team_id: str, agent_id: str) -> List[Role]:
        """Get roles for an agent in a team."""
        roles = []
        for role_id, agents in self._assignments[team_id].items():
            if agent_id in agents:
                role = self._roles.get(role_id)
                if role:
                    roles.append(role)
        return roles

    def get_agents_with_role(self, team_id: str, role_id: str) -> Set[str]:
        """Get agents with a specific role."""
        return self._assignments[team_id].get(role_id, set()).copy()


# =============================================================================
# TEAM MANAGER
# =============================================================================

class TeamManager:
    """Manage collaboration teams."""

    def __init__(self):
        self._teams: Dict[str, Team] = {}
        self._by_member: Dict[str, Set[str]] = defaultdict(set)

    def create_team(
        self,
        name: str,
        goal: str = "",
        collab_type: CollaborationType = CollaborationType.COOPERATIVE,
        leader_id: Optional[str] = None
    ) -> Team:
        """Create a team."""
        team = Team(
            name=name,
            goal=goal,
            collab_type=collab_type,
            leader_id=leader_id
        )

        self._teams[team.team_id] = team

        return team

    def disband_team(self, team_id: str) -> Optional[Team]:
        """Disband a team."""
        team = self._teams.get(team_id)
        if not team:
            return None

        team.status = TeamStatus.DISBANDED

        for member_id in team.members:
            self._by_member[member_id].discard(team_id)

        return team

    def add_member(
        self,
        team_id: str,
        agent_id: str,
        name: str = "",
        capabilities: Optional[List[AgentCapability]] = None
    ) -> Optional[TeamMember]:
        """Add a member to a team."""
        team = self._teams.get(team_id)
        if not team:
            return None

        member = TeamMember(
            agent_id=agent_id,
            name=name or agent_id,
            capabilities=capabilities or []
        )

        team.members[agent_id] = member
        self._by_member[agent_id].add(team_id)

        if team.status == TeamStatus.FORMING and len(team.members) >= 2:
            team.status = TeamStatus.ACTIVE

        return member

    def remove_member(self, team_id: str, agent_id: str) -> bool:
        """Remove a member from a team."""
        team = self._teams.get(team_id)
        if not team or agent_id not in team.members:
            return False

        del team.members[agent_id]
        self._by_member[agent_id].discard(team_id)

        if team.leader_id == agent_id:
            if team.members:
                team.leader_id = next(iter(team.members))
            else:
                team.leader_id = None

        return True

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team."""
        return self._teams.get(team_id)

    def get_member(self, team_id: str, agent_id: str) -> Optional[TeamMember]:
        """Get a team member."""
        team = self._teams.get(team_id)
        if not team:
            return None
        return team.members.get(agent_id)

    def get_agent_teams(self, agent_id: str) -> List[Team]:
        """Get teams for an agent."""
        team_ids = self._by_member.get(agent_id, set())
        return [self._teams[tid] for tid in team_ids if tid in self._teams]

    def set_status(self, team_id: str, status: TeamStatus) -> bool:
        """Set team status."""
        team = self._teams.get(team_id)
        if not team:
            return False

        team.status = status
        return True

    def set_leader(self, team_id: str, agent_id: str) -> bool:
        """Set team leader."""
        team = self._teams.get(team_id)
        if not team or agent_id not in team.members:
            return False

        team.leader_id = agent_id
        return True

    @property
    def active_teams(self) -> List[Team]:
        """Get active teams."""
        return [t for t in self._teams.values() if t.status in {TeamStatus.ACTIVE, TeamStatus.WORKING}]


# =============================================================================
# TASK ALLOCATOR
# =============================================================================

class TaskAllocator:
    """Allocate tasks to team members."""

    def __init__(self, capability_manager: CapabilityManager):
        self._capability_manager = capability_manager
        self._allocation_counts: Dict[str, int] = defaultdict(int)

    def allocate(
        self,
        task: CollaborativeTask,
        team: Team,
        strategy: TaskAllocation = TaskAllocation.CAPABILITY
    ) -> Set[str]:
        """Allocate a task to team members."""
        if strategy == TaskAllocation.ROUND_ROBIN:
            return self._round_robin(task, team)
        elif strategy == TaskAllocation.CAPABILITY:
            return self._capability_based(task, team)
        elif strategy == TaskAllocation.LOAD_BALANCE:
            return self._load_balance(task, team)
        else:
            return self._capability_based(task, team)

    def _round_robin(self, task: CollaborativeTask, team: Team) -> Set[str]:
        """Round robin allocation."""
        members = list(team.members.keys())
        if not members:
            return set()

        counts = [(m, self._allocation_counts[m]) for m in members]
        counts.sort(key=lambda x: x[1])

        selected = counts[0][0]
        self._allocation_counts[selected] += 1

        return {selected}

    def _capability_based(self, task: CollaborativeTask, team: Team) -> Set[str]:
        """Capability-based allocation."""
        if not task.required_capabilities:
            return {next(iter(team.members))} if team.members else set()

        scores = []

        for agent_id in team.members:
            score = self._capability_manager.match_requirements(
                agent_id,
                task.required_capabilities
            )
            scores.append((agent_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        if scores and scores[0][1] > 0:
            return {scores[0][0]}

        return {next(iter(team.members))} if team.members else set()

    def _load_balance(self, task: CollaborativeTask, team: Team) -> Set[str]:
        """Load-balanced allocation."""
        members = list(team.members.values())
        if not members:
            return set()

        members.sort(key=lambda m: m.workload)

        available = [m for m in members if m.availability > 0.1]
        if not available:
            available = members

        return {available[0].agent_id}


# =============================================================================
# KNOWLEDGE POOL
# =============================================================================

class KnowledgePool:
    """Shared knowledge pool for teams."""

    def __init__(self):
        self._knowledge: Dict[str, SharedKnowledge] = {}
        self._by_team: Dict[str, Set[str]] = defaultdict(set)
        self._by_type: Dict[str, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

    def share(
        self,
        team_id: str,
        contributor_id: str,
        content: Any,
        knowledge_type: str = "general",
        tags: Optional[Set[str]] = None
    ) -> SharedKnowledge:
        """Share knowledge."""
        knowledge = SharedKnowledge(
            team_id=team_id,
            contributor_id=contributor_id,
            content=content,
            knowledge_type=knowledge_type,
            tags=tags or set()
        )

        self._knowledge[knowledge.knowledge_id] = knowledge
        self._by_team[team_id].add(knowledge.knowledge_id)
        self._by_type[knowledge_type].add(knowledge.knowledge_id)

        for tag in knowledge.tags:
            self._by_tag[tag].add(knowledge.knowledge_id)

        return knowledge

    def get(self, knowledge_id: str) -> Optional[SharedKnowledge]:
        """Get knowledge item."""
        knowledge = self._knowledge.get(knowledge_id)
        if knowledge:
            knowledge.access_count += 1
        return knowledge

    def get_team_knowledge(self, team_id: str) -> List[SharedKnowledge]:
        """Get all knowledge for a team."""
        kid_set = self._by_team.get(team_id, set())
        return [self._knowledge[kid] for kid in kid_set if kid in self._knowledge]

    def search_by_type(self, knowledge_type: str) -> List[SharedKnowledge]:
        """Search knowledge by type."""
        kid_set = self._by_type.get(knowledge_type, set())
        return [self._knowledge[kid] for kid in kid_set if kid in self._knowledge]

    def search_by_tag(self, tag: str) -> List[SharedKnowledge]:
        """Search knowledge by tag."""
        kid_set = self._by_tag.get(tag, set())
        return [self._knowledge[kid] for kid in kid_set if kid in self._knowledge]


# =============================================================================
# CONTRIBUTION TRACKER
# =============================================================================

class ContributionTracker:
    """Track team contributions."""

    def __init__(self):
        self._contributions: Dict[str, Contribution] = {}
        self._by_agent: Dict[str, List[str]] = defaultdict(list)
        self._by_team: Dict[str, List[str]] = defaultdict(list)
        self._scores: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def record(
        self,
        agent_id: str,
        team_id: str,
        contribution_type: ContributionType,
        value: float = 1.0,
        task_id: Optional[str] = None,
        description: str = ""
    ) -> Contribution:
        """Record a contribution."""
        contribution = Contribution(
            agent_id=agent_id,
            team_id=team_id,
            contribution_type=contribution_type,
            value=value,
            task_id=task_id,
            description=description
        )

        self._contributions[contribution.contribution_id] = contribution
        self._by_agent[agent_id].append(contribution.contribution_id)
        self._by_team[team_id].append(contribution.contribution_id)

        self._scores[team_id][agent_id] += value

        return contribution

    def get_agent_contributions(self, agent_id: str) -> List[Contribution]:
        """Get contributions by agent."""
        cids = self._by_agent.get(agent_id, [])
        return [self._contributions[cid] for cid in cids if cid in self._contributions]

    def get_team_contributions(self, team_id: str) -> List[Contribution]:
        """Get contributions in a team."""
        cids = self._by_team.get(team_id, [])
        return [self._contributions[cid] for cid in cids if cid in self._contributions]

    def get_score(self, team_id: str, agent_id: str) -> float:
        """Get contribution score."""
        return self._scores[team_id][agent_id]

    def get_team_scores(self, team_id: str) -> Dict[str, float]:
        """Get all scores in a team."""
        return dict(self._scores[team_id])

    def get_leaderboard(self, team_id: str) -> List[Tuple[str, float]]:
        """Get team leaderboard."""
        scores = self._scores[team_id]
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# =============================================================================
# SYNERGY CALCULATOR
# =============================================================================

class SynergyCalculator:
    """Calculate team synergy."""

    def __init__(self, capability_manager: CapabilityManager):
        self._capability_manager = capability_manager

    def calculate_synergy(self, team: Team) -> float:
        """Calculate team synergy score."""
        if len(team.members) < 2:
            return 0.0

        scores = []

        skill_diversity = self._skill_diversity(team)
        scores.append(skill_diversity)

        capability_coverage = self._capability_coverage(team)
        scores.append(capability_coverage)

        workload_balance = self._workload_balance(team)
        scores.append(workload_balance)

        availability_score = self._availability_score(team)
        scores.append(availability_score)

        return sum(scores) / len(scores)

    def _skill_diversity(self, team: Team) -> float:
        """Calculate skill diversity."""
        all_domains: Set[str] = set()

        for member in team.members.values():
            for cap in member.capabilities:
                all_domains.update(cap.domains)

        n = len(team.members)
        if n == 0:
            return 0.0

        diversity = len(all_domains) / n
        return min(1.0, diversity)

    def _capability_coverage(self, team: Team) -> float:
        """Calculate capability coverage."""
        all_caps: Set[str] = set()
        member_count = len(team.members)

        for member in team.members.values():
            for cap in member.capabilities:
                all_caps.add(cap.name)

        if member_count == 0:
            return 0.0

        return min(1.0, len(all_caps) / (member_count * 2))

    def _workload_balance(self, team: Team) -> float:
        """Calculate workload balance."""
        workloads = [m.workload for m in team.members.values()]

        if not workloads:
            return 1.0

        avg = sum(workloads) / len(workloads)
        if avg == 0:
            return 1.0

        variance = sum((w - avg) ** 2 for w in workloads) / len(workloads)
        std_dev = math.sqrt(variance)

        return max(0.0, 1.0 - std_dev)

    def _availability_score(self, team: Team) -> float:
        """Calculate availability score."""
        availabilities = [m.availability for m in team.members.values()]

        if not availabilities:
            return 0.0

        return sum(availabilities) / len(availabilities)


# =============================================================================
# COLLABORATION ENGINE
# =============================================================================

class CollaborationEngine:
    """
    Collaboration Engine for BAEL.

    Multi-agent collaboration and teamwork.
    """

    def __init__(self):
        self._capabilities = CapabilityManager()
        self._roles = RoleManager()
        self._teams = TeamManager()
        self._knowledge = KnowledgePool()
        self._contributions = ContributionTracker()
        self._synergy = SynergyCalculator(self._capabilities)
        self._allocator = TaskAllocator(self._capabilities)

        self._tasks: Dict[str, CollaborativeTask] = {}
        self._by_team: Dict[str, Set[str]] = defaultdict(set)

        self._stats = CollaborationStats()

    def register_capability(
        self,
        agent_id: str,
        name: str,
        skill_level: float = 0.5,
        domains: Optional[Set[str]] = None
    ) -> AgentCapability:
        """Register an agent capability."""
        return self._capabilities.register(agent_id, name, skill_level, domains)

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Get agent capabilities."""
        return self._capabilities.get_agent_capabilities(agent_id)

    def define_role(
        self,
        name: str,
        role_type: RoleType = RoleType.EXECUTOR,
        required_capabilities: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None
    ) -> Role:
        """Define a team role."""
        return self._roles.define_role(
            name, role_type, required_capabilities, permissions
        )

    def create_team(
        self,
        name: str,
        goal: str = "",
        collab_type: CollaborationType = CollaborationType.COOPERATIVE
    ) -> Team:
        """Create a collaboration team."""
        team = self._teams.create_team(name, goal, collab_type)
        self._stats.teams_formed += 1
        return team

    def disband_team(self, team_id: str) -> Optional[Team]:
        """Disband a team."""
        return self._teams.disband_team(team_id)

    def add_team_member(
        self,
        team_id: str,
        agent_id: str,
        name: str = ""
    ) -> Optional[TeamMember]:
        """Add a member to a team."""
        capabilities = self._capabilities.get_agent_capabilities(agent_id)
        return self._teams.add_member(team_id, agent_id, name, capabilities)

    def remove_team_member(self, team_id: str, agent_id: str) -> bool:
        """Remove a member from a team."""
        return self._teams.remove_member(team_id, agent_id)

    def assign_role(
        self,
        team_id: str,
        agent_id: str,
        role_id: str
    ) -> bool:
        """Assign a role to a team member."""
        if not self._roles.assign_role(team_id, agent_id, role_id):
            return False

        member = self._teams.get_member(team_id, agent_id)
        if member:
            member.roles.add(role_id)

        return True

    def unassign_role(
        self,
        team_id: str,
        agent_id: str,
        role_id: str
    ) -> bool:
        """Unassign a role from a team member."""
        if not self._roles.unassign_role(team_id, agent_id, role_id):
            return False

        member = self._teams.get_member(team_id, agent_id)
        if member:
            member.roles.discard(role_id)

        return True

    def set_team_leader(self, team_id: str, agent_id: str) -> bool:
        """Set team leader."""
        return self._teams.set_leader(team_id, agent_id)

    def create_task(
        self,
        team_id: str,
        name: str,
        description: str = "",
        required_capabilities: Optional[List[str]] = None,
        deadline: Optional[datetime] = None
    ) -> CollaborativeTask:
        """Create a collaborative task."""
        task = CollaborativeTask(
            name=name,
            description=description,
            team_id=team_id,
            required_capabilities=required_capabilities or [],
            deadline=deadline
        )

        self._tasks[task.task_id] = task
        self._by_team[team_id].add(task.task_id)

        return task

    def allocate_task(
        self,
        task_id: str,
        strategy: TaskAllocation = TaskAllocation.CAPABILITY
    ) -> Set[str]:
        """Allocate a task to team members."""
        task = self._tasks.get(task_id)
        if not task:
            return set()

        team = self._teams.get_team(task.team_id)
        if not team:
            return set()

        assigned = self._allocator.allocate(task, team, strategy)
        task.assigned_to = assigned

        for agent_id in assigned:
            member = self._teams.get_member(task.team_id, agent_id)
            if member:
                member.workload += 0.1

        return assigned

    def complete_task(
        self,
        task_id: str,
        contributor_id: str
    ) -> bool:
        """Mark a task as complete."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = "completed"
        task.progress = 1.0

        self._contributions.record(
            agent_id=contributor_id,
            team_id=task.team_id,
            contribution_type=ContributionType.TASK_COMPLETE,
            value=1.0,
            task_id=task_id,
            description=f"Completed: {task.name}"
        )

        self._stats.tasks_completed += 1

        for agent_id in task.assigned_to:
            member = self._teams.get_member(task.team_id, agent_id)
            if member:
                member.workload = max(0, member.workload - 0.1)

        return True

    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """Update task progress."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.progress = max(0.0, min(1.0, progress))

        if task.progress >= 1.0:
            task.status = "completed"
        elif task.progress > 0:
            task.status = "in_progress"

        return True

    def share_knowledge(
        self,
        team_id: str,
        contributor_id: str,
        content: Any,
        knowledge_type: str = "general",
        tags: Optional[Set[str]] = None
    ) -> SharedKnowledge:
        """Share knowledge with the team."""
        knowledge = self._knowledge.share(
            team_id, contributor_id, content, knowledge_type, tags
        )

        self._contributions.record(
            agent_id=contributor_id,
            team_id=team_id,
            contribution_type=ContributionType.KNOWLEDGE_SHARE,
            value=0.5,
            description=f"Shared: {knowledge_type}"
        )

        self._stats.knowledge_shared += 1

        return knowledge

    def get_team_knowledge(self, team_id: str) -> List[SharedKnowledge]:
        """Get team knowledge."""
        return self._knowledge.get_team_knowledge(team_id)

    def record_contribution(
        self,
        agent_id: str,
        team_id: str,
        contribution_type: ContributionType,
        value: float = 1.0,
        description: str = ""
    ) -> Contribution:
        """Record a contribution."""
        contribution = self._contributions.record(
            agent_id, team_id, contribution_type, value, description=description
        )

        self._stats.total_contributions += 1

        return contribution

    def get_contribution_score(self, team_id: str, agent_id: str) -> float:
        """Get contribution score."""
        return self._contributions.get_score(team_id, agent_id)

    def get_leaderboard(self, team_id: str) -> List[Tuple[str, float]]:
        """Get team leaderboard."""
        return self._contributions.get_leaderboard(team_id)

    def calculate_synergy(self, team_id: str) -> float:
        """Calculate team synergy."""
        team = self._teams.get_team(team_id)
        if not team:
            return 0.0

        synergy = self._synergy.calculate_synergy(team)
        self._stats.synergy_score = synergy

        return synergy

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team."""
        return self._teams.get_team(team_id)

    def get_active_teams(self) -> List[Team]:
        """Get active teams."""
        return self._teams.active_teams

    def get_agent_teams(self, agent_id: str) -> List[Team]:
        """Get teams for an agent."""
        return self._teams.get_agent_teams(agent_id)

    def get_team_tasks(self, team_id: str) -> List[CollaborativeTask]:
        """Get tasks for a team."""
        task_ids = self._by_team.get(team_id, set())
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_task(self, task_id: str) -> Optional[CollaborativeTask]:
        """Get a task."""
        return self._tasks.get(task_id)

    @property
    def stats(self) -> CollaborationStats:
        """Get collaboration statistics."""
        if self._teams.active_teams:
            total_members = sum(len(t.members) for t in self._teams.active_teams)
            self._stats.avg_team_size = total_members / len(self._teams.active_teams)

        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "teams_formed": self._stats.teams_formed,
            "active_teams": len(self._teams.active_teams),
            "tasks_completed": self._stats.tasks_completed,
            "pending_tasks": len([t for t in self._tasks.values() if t.status == "pending"]),
            "knowledge_shared": self._stats.knowledge_shared,
            "total_contributions": self._stats.total_contributions,
            "avg_team_size": self._stats.avg_team_size,
            "synergy_score": self._stats.synergy_score
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Collaboration Engine."""
    print("=" * 70)
    print("BAEL - COLLABORATION ENGINE DEMO")
    print("Multi-agent Collaboration and Teamwork")
    print("=" * 70)
    print()

    engine = CollaborationEngine()

    # 1. Register Capabilities
    print("1. REGISTER CAPABILITIES:")
    print("-" * 40)

    cap1 = engine.register_capability(
        "agent_1", "coding", skill_level=0.9, domains={"python", "javascript"}
    )
    cap2 = engine.register_capability(
        "agent_1", "analysis", skill_level=0.7, domains={"data"}
    )

    cap3 = engine.register_capability(
        "agent_2", "research", skill_level=0.85, domains={"web", "academic"}
    )

    cap4 = engine.register_capability(
        "agent_3", "writing", skill_level=0.8, domains={"technical", "creative"}
    )

    print(f"   agent_1 capabilities: coding, analysis")
    print(f"   agent_2 capabilities: research")
    print(f"   agent_3 capabilities: writing")
    print()

    # 2. Define Roles
    print("2. DEFINE ROLES:")
    print("-" * 40)

    leader_role = engine.define_role(
        "Team Lead",
        role_type=RoleType.LEADER,
        permissions={"assign_tasks", "manage_team"}
    )

    dev_role = engine.define_role(
        "Developer",
        role_type=RoleType.EXECUTOR,
        required_capabilities=["coding"]
    )

    analyst_role = engine.define_role(
        "Analyst",
        role_type=RoleType.ANALYST,
        required_capabilities=["research", "analysis"]
    )

    print(f"   Defined: Team Lead, Developer, Analyst")
    print()

    # 3. Create Team
    print("3. CREATE TEAM:")
    print("-" * 40)

    team = engine.create_team(
        name="Project Alpha",
        goal="Complete the AI system",
        collab_type=CollaborationType.COOPERATIVE
    )

    print(f"   Team: {team.name}")
    print(f"   Goal: {team.goal}")
    print(f"   Type: {team.collab_type.value}")
    print()

    # 4. Add Members
    print("4. ADD TEAM MEMBERS:")
    print("-" * 40)

    engine.add_team_member(team.team_id, "agent_1", "Alice")
    engine.add_team_member(team.team_id, "agent_2", "Bob")
    engine.add_team_member(team.team_id, "agent_3", "Charlie")

    engine.set_team_leader(team.team_id, "agent_1")

    print(f"   Members: Alice, Bob, Charlie")
    print(f"   Leader: agent_1 (Alice)")
    print(f"   Team Status: {team.status.value}")
    print()

    # 5. Assign Roles
    print("5. ASSIGN ROLES:")
    print("-" * 40)

    engine.assign_role(team.team_id, "agent_1", leader_role.role_id)
    engine.assign_role(team.team_id, "agent_1", dev_role.role_id)
    engine.assign_role(team.team_id, "agent_2", analyst_role.role_id)

    print(f"   agent_1: Team Lead, Developer")
    print(f"   agent_2: Analyst")
    print()

    # 6. Create Tasks
    print("6. CREATE COLLABORATIVE TASKS:")
    print("-" * 40)

    task1 = engine.create_task(
        team_id=team.team_id,
        name="Build Data Pipeline",
        description="Create data processing pipeline",
        required_capabilities=["coding", "analysis"]
    )

    task2 = engine.create_task(
        team_id=team.team_id,
        name="Research Best Practices",
        required_capabilities=["research"]
    )

    task3 = engine.create_task(
        team_id=team.team_id,
        name="Write Documentation",
        required_capabilities=["writing"]
    )

    print(f"   Task 1: {task1.name}")
    print(f"   Task 2: {task2.name}")
    print(f"   Task 3: {task3.name}")
    print()

    # 7. Allocate Tasks
    print("7. ALLOCATE TASKS:")
    print("-" * 40)

    assigned1 = engine.allocate_task(task1.task_id, TaskAllocation.CAPABILITY)
    assigned2 = engine.allocate_task(task2.task_id, TaskAllocation.CAPABILITY)
    assigned3 = engine.allocate_task(task3.task_id, TaskAllocation.CAPABILITY)

    print(f"   Task 1 -> {assigned1}")
    print(f"   Task 2 -> {assigned2}")
    print(f"   Task 3 -> {assigned3}")
    print()

    # 8. Update Progress
    print("8. UPDATE TASK PROGRESS:")
    print("-" * 40)

    engine.update_task_progress(task1.task_id, 0.5)
    engine.update_task_progress(task2.task_id, 0.8)
    engine.complete_task(task3.task_id, "agent_3")

    print(f"   Task 1 progress: 50%")
    print(f"   Task 2 progress: 80%")
    print(f"   Task 3: Completed!")
    print()

    # 9. Share Knowledge
    print("9. SHARE KNOWLEDGE:")
    print("-" * 40)

    knowledge = engine.share_knowledge(
        team_id=team.team_id,
        contributor_id="agent_2",
        content={"findings": "AI best practices", "sources": 5},
        knowledge_type="research",
        tags={"ai", "best-practices"}
    )

    print(f"   Shared: {knowledge.knowledge_type}")
    print(f"   Tags: {knowledge.tags}")
    print(f"   Contributor: {knowledge.contributor_id}")
    print()

    # 10. Record Contributions
    print("10. RECORD CONTRIBUTIONS:")
    print("-" * 40)

    engine.record_contribution(
        "agent_1", team.team_id,
        ContributionType.ASSISTANCE,
        value=0.5,
        description="Helped with code review"
    )

    engine.record_contribution(
        "agent_1", team.team_id,
        ContributionType.COORDINATION,
        value=0.3,
        description="Coordinated team meeting"
    )

    print(f"   Recorded contributions for team")
    print()

    # 11. Leaderboard
    print("11. CONTRIBUTION LEADERBOARD:")
    print("-" * 40)

    leaderboard = engine.get_leaderboard(team.team_id)

    for rank, (agent_id, score) in enumerate(leaderboard, 1):
        print(f"   #{rank} {agent_id}: {score:.2f}")
    print()

    # 12. Calculate Synergy
    print("12. TEAM SYNERGY:")
    print("-" * 40)

    synergy = engine.calculate_synergy(team.team_id)

    print(f"   Synergy Score: {synergy:.2f}")
    print()

    # 13. Statistics
    print("13. COLLABORATION STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Teams Formed: {stats.teams_formed}")
    print(f"   Tasks Completed: {stats.tasks_completed}")
    print(f"   Knowledge Shared: {stats.knowledge_shared}")
    print(f"   Total Contributions: {stats.total_contributions}")
    print(f"   Avg Team Size: {stats.avg_team_size:.1f}")
    print()

    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Collaboration Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
