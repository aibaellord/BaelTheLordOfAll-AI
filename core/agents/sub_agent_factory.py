"""
BAEL - Sub-Agent Factory
========================

Create specialized agents for ANY task. Unlimited agents. Unlimited power.

Features:
1. Agent Generation - Create agents for any task
2. Specialization Engine - Deep specialization
3. Agent Cloning - Clone successful agents
4. Agent Evolution - Evolve better agents
5. Agent Orchestration - Coordinate all agents
6. Agent Fusion - Combine agent capabilities
7. Agent Hierarchy - Multi-level agent structures
8. Agent Communication - Inter-agent messaging
9. Agent Performance Tracking - Monitor all agents
10. Agent Optimization - Continuously improve

"One agent is powerful. A million agents are unstoppable."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.AGENTS")


class AgentType(Enum):
    """Types of sub-agents."""
    RESEARCHER = "researcher"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    MONITOR = "monitor"
    STRATEGIST = "strategist"
    INFILTRATOR = "infiltrator"
    DEFENDER = "defender"
    OPTIMIZER = "optimizer"
    COMMUNICATOR = "communicator"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    HUNTER = "hunter"


class AgentState(Enum):
    """Agent operational states."""
    IDLE = "idle"
    ACTIVE = "active"
    WORKING = "working"
    WAITING = "waiting"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


class SpecializationLevel(Enum):
    """Levels of agent specialization."""
    GENERALIST = 1
    BASIC = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6
    TRANSCENDENT = 7


class AgentPriority(Enum):
    """Agent task priority."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class AgentCapability:
    """A capability that an agent possesses."""
    name: str
    level: float  # 0-1 proficiency
    experience: int  # Number of times used
    success_rate: float  # Historical success


@dataclass
class AgentConfiguration:
    """Configuration for creating an agent."""
    type: AgentType
    name: str
    specializations: List[str]
    capabilities: List[str]
    priority: AgentPriority
    max_concurrent_tasks: int = 5
    autonomous: bool = True
    learning_enabled: bool = True
    communication_enabled: bool = True


@dataclass
class SubAgent:
    """A sub-agent instance."""
    id: str
    name: str
    type: AgentType
    state: AgentState
    specialization_level: SpecializationLevel
    capabilities: Dict[str, AgentCapability]
    current_tasks: List[str]
    completed_tasks: int
    success_rate: float
    parent_id: Optional[str]
    children_ids: List[str]
    created_at: datetime
    last_active: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "state": self.state.value,
            "specialization": self.specialization_level.name,
            "capabilities": len(self.capabilities),
            "completed_tasks": self.completed_tasks,
            "success_rate": f"{self.success_rate:.0%}"
        }


@dataclass
class AgentTask:
    """A task for an agent."""
    id: str
    description: str
    agent_id: str
    priority: AgentPriority
    parameters: Dict[str, Any]
    status: str  # pending, running, completed, failed
    result: Optional[Any] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AgentMessage:
    """A message between agents."""
    id: str
    from_agent: str
    to_agent: str
    content: Any
    timestamp: datetime
    acknowledged: bool = False


@dataclass
class AgentEvolution:
    """Evolution record for an agent."""
    agent_id: str
    generation: int
    fitness_score: float
    mutations: List[str]
    parent_fitness: float
    improvement: float


class SubAgentFactory:
    """
    The Sub-Agent Factory - creates unlimited specialized agents.

    Provides:
    - Agent creation for any task
    - Agent specialization and evolution
    - Agent orchestration and coordination
    - Agent cloning and fusion
    - Performance optimization
    """

    def __init__(self):
        self.agents: Dict[str, SubAgent] = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.messages: List[AgentMessage] = []
        self.evolutions: List[AgentEvolution] = []
        self.agent_templates: Dict[str, AgentConfiguration] = {}
        self.agent_hierarchy: Dict[str, List[str]] = {}  # parent -> children

        # Predefined agent templates
        self._init_templates()

        logger.info("SubAgentFactory initialized - agent army ready")

    def _init_templates(self):
        """Initialize predefined agent templates."""
        self.agent_templates = {
            "researcher": AgentConfiguration(
                type=AgentType.RESEARCHER,
                name="Research Agent",
                specializations=["information_gathering", "analysis", "synthesis"],
                capabilities=["search", "summarize", "analyze", "report"],
                priority=AgentPriority.NORMAL
            ),
            "executor": AgentConfiguration(
                type=AgentType.EXECUTOR,
                name="Execution Agent",
                specializations=["task_execution", "automation", "integration"],
                capabilities=["execute", "automate", "integrate", "validate"],
                priority=AgentPriority.HIGH
            ),
            "strategist": AgentConfiguration(
                type=AgentType.STRATEGIST,
                name="Strategy Agent",
                specializations=["planning", "optimization", "prediction"],
                capabilities=["plan", "optimize", "predict", "evaluate"],
                priority=AgentPriority.HIGH
            ),
            "infiltrator": AgentConfiguration(
                type=AgentType.INFILTRATOR,
                name="Infiltration Agent",
                specializations=["stealth", "access", "extraction"],
                capabilities=["infiltrate", "extract", "evade", "persist"],
                priority=AgentPriority.CRITICAL
            ),
            "defender": AgentConfiguration(
                type=AgentType.DEFENDER,
                name="Defense Agent",
                specializations=["security", "monitoring", "response"],
                capabilities=["monitor", "detect", "defend", "respond"],
                priority=AgentPriority.CRITICAL
            ),
            "hunter": AgentConfiguration(
                type=AgentType.HUNTER,
                name="Hunter Agent",
                specializations=["tracking", "analysis", "pursuit"],
                capabilities=["track", "analyze", "pursue", "capture"],
                priority=AgentPriority.HIGH
            ),
            "optimizer": AgentConfiguration(
                type=AgentType.OPTIMIZER,
                name="Optimization Agent",
                specializations=["performance", "efficiency", "resource_management"],
                capabilities=["analyze", "optimize", "benchmark", "tune"],
                priority=AgentPriority.NORMAL
            ),
            "coordinator": AgentConfiguration(
                type=AgentType.COORDINATOR,
                name="Coordinator Agent",
                specializations=["orchestration", "communication", "scheduling"],
                capabilities=["coordinate", "schedule", "communicate", "synchronize"],
                priority=AgentPriority.HIGH
            )
        }

    # -------------------------------------------------------------------------
    # AGENT CREATION
    # -------------------------------------------------------------------------

    async def create_agent(
        self,
        config: AgentConfiguration
    ) -> SubAgent:
        """Create a new sub-agent."""
        # Build capabilities
        capabilities = {}
        for cap_name in config.capabilities:
            capabilities[cap_name] = AgentCapability(
                name=cap_name,
                level=random.uniform(0.5, 0.8),
                experience=0,
                success_rate=0.8
            )

        agent = SubAgent(
            id=self._gen_id("agent"),
            name=config.name,
            type=config.type,
            state=AgentState.IDLE,
            specialization_level=SpecializationLevel.BASIC,
            capabilities=capabilities,
            current_tasks=[],
            completed_tasks=0,
            success_rate=0.8,
            parent_id=None,
            children_ids=[],
            created_at=datetime.now(),
            last_active=datetime.now(),
            metadata={
                "specializations": config.specializations,
                "priority": config.priority.value,
                "autonomous": config.autonomous,
                "learning": config.learning_enabled
            }
        )

        self.agents[agent.id] = agent
        logger.info(f"Created agent: {agent.name} ({agent.type.value})")

        return agent

    async def create_from_template(
        self,
        template_name: str,
        custom_name: Optional[str] = None
    ) -> SubAgent:
        """Create an agent from a predefined template."""
        template = self.agent_templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        config = AgentConfiguration(
            type=template.type,
            name=custom_name or template.name,
            specializations=template.specializations,
            capabilities=template.capabilities,
            priority=template.priority,
            max_concurrent_tasks=template.max_concurrent_tasks,
            autonomous=template.autonomous,
            learning_enabled=template.learning_enabled,
            communication_enabled=template.communication_enabled
        )

        return await self.create_agent(config)

    async def create_specialized_agent(
        self,
        name: str,
        specialization: str,
        capabilities: List[str]
    ) -> SubAgent:
        """Create a highly specialized agent."""
        config = AgentConfiguration(
            type=AgentType.SPECIALIST,
            name=name,
            specializations=[specialization],
            capabilities=capabilities,
            priority=AgentPriority.HIGH,
            autonomous=True,
            learning_enabled=True
        )

        agent = await self.create_agent(config)
        agent.specialization_level = SpecializationLevel.EXPERT

        return agent

    async def create_agent_army(
        self,
        template_name: str,
        count: int,
        name_prefix: str = "Agent"
    ) -> List[SubAgent]:
        """Create an army of agents from a template."""
        agents = []

        for i in range(count):
            agent = await self.create_from_template(
                template_name,
                f"{name_prefix}_{i+1}"
            )
            agents.append(agent)

        return agents

    # -------------------------------------------------------------------------
    # AGENT CLONING & EVOLUTION
    # -------------------------------------------------------------------------

    async def clone_agent(
        self,
        agent_id: str,
        new_name: Optional[str] = None
    ) -> SubAgent:
        """Clone an existing agent."""
        original = self.agents.get(agent_id)
        if not original:
            raise ValueError(f"Agent not found: {agent_id}")

        # Deep copy capabilities
        cloned_capabilities = {}
        for cap_name, cap in original.capabilities.items():
            cloned_capabilities[cap_name] = AgentCapability(
                name=cap.name,
                level=cap.level,
                experience=0,  # Fresh start
                success_rate=cap.success_rate
            )

        clone = SubAgent(
            id=self._gen_id("clone"),
            name=new_name or f"{original.name}_clone",
            type=original.type,
            state=AgentState.IDLE,
            specialization_level=original.specialization_level,
            capabilities=cloned_capabilities,
            current_tasks=[],
            completed_tasks=0,
            success_rate=original.success_rate,
            parent_id=original.id,
            children_ids=[],
            created_at=datetime.now(),
            last_active=datetime.now(),
            metadata=original.metadata.copy()
        )

        self.agents[clone.id] = clone
        original.children_ids.append(clone.id)

        return clone

    async def evolve_agent(
        self,
        agent_id: str,
        mutation_rate: float = 0.1
    ) -> SubAgent:
        """Evolve an agent to create an improved version."""
        original = self.agents.get(agent_id)
        if not original:
            raise ValueError(f"Agent not found: {agent_id}")

        # Clone first
        evolved = await self.clone_agent(agent_id, f"{original.name}_evolved")

        # Apply mutations
        mutations = []
        for cap_name, cap in evolved.capabilities.items():
            if random.random() < mutation_rate:
                # Mutate capability level
                mutation = random.uniform(-0.1, 0.2)  # Slight bias toward improvement
                cap.level = max(0, min(1, cap.level + mutation))
                mutations.append(f"{cap_name}: {mutation:+.2f}")

        # Chance to gain new capability
        if random.random() < mutation_rate:
            new_cap_name = f"evolved_capability_{len(evolved.capabilities)}"
            evolved.capabilities[new_cap_name] = AgentCapability(
                name=new_cap_name,
                level=random.uniform(0.3, 0.6),
                experience=0,
                success_rate=0.7
            )
            mutations.append(f"New: {new_cap_name}")

        # Potentially increase specialization
        if random.random() < 0.3:
            current_level = evolved.specialization_level.value
            if current_level < SpecializationLevel.TRANSCENDENT.value:
                evolved.specialization_level = SpecializationLevel(current_level + 1)
                mutations.append(f"Specialization: {evolved.specialization_level.name}")

        # Record evolution
        evolution = AgentEvolution(
            agent_id=evolved.id,
            generation=1,
            fitness_score=self._calculate_fitness(evolved),
            mutations=mutations,
            parent_fitness=self._calculate_fitness(original),
            improvement=self._calculate_fitness(evolved) - self._calculate_fitness(original)
        )
        self.evolutions.append(evolution)

        return evolved

    async def fuse_agents(
        self,
        agent_ids: List[str],
        new_name: str
    ) -> SubAgent:
        """Fuse multiple agents into one super-agent."""
        agents = [self.agents.get(aid) for aid in agent_ids]
        agents = [a for a in agents if a is not None]

        if len(agents) < 2:
            raise ValueError("Need at least 2 agents to fuse")

        # Combine capabilities - take the best of each
        combined_capabilities = {}
        for agent in agents:
            for cap_name, cap in agent.capabilities.items():
                if cap_name not in combined_capabilities:
                    combined_capabilities[cap_name] = AgentCapability(
                        name=cap_name,
                        level=cap.level,
                        experience=cap.experience,
                        success_rate=cap.success_rate
                    )
                else:
                    existing = combined_capabilities[cap_name]
                    if cap.level > existing.level:
                        combined_capabilities[cap_name] = AgentCapability(
                            name=cap_name,
                            level=cap.level,
                            experience=max(existing.experience, cap.experience),
                            success_rate=max(existing.success_rate, cap.success_rate)
                        )

        # Create fused agent
        fused = SubAgent(
            id=self._gen_id("fused"),
            name=new_name,
            type=AgentType.SPECIALIST,
            state=AgentState.IDLE,
            specialization_level=SpecializationLevel.MASTER,
            capabilities=combined_capabilities,
            current_tasks=[],
            completed_tasks=sum(a.completed_tasks for a in agents),
            success_rate=max(a.success_rate for a in agents),
            parent_id=None,
            children_ids=[],
            created_at=datetime.now(),
            last_active=datetime.now(),
            metadata={
                "fused_from": agent_ids,
                "fusion_time": datetime.now().isoformat()
            }
        )

        self.agents[fused.id] = fused

        return fused

    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------

    async def assign_task(
        self,
        agent_id: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: AgentPriority = AgentPriority.NORMAL
    ) -> AgentTask:
        """Assign a task to an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        task = AgentTask(
            id=self._gen_id("task"),
            description=description,
            agent_id=agent_id,
            priority=priority,
            parameters=parameters or {},
            status="pending"
        )

        self.tasks[task.id] = task
        agent.current_tasks.append(task.id)
        agent.state = AgentState.WORKING
        agent.last_active = datetime.now()

        return task

    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute an assigned task."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        agent = self.agents.get(task.agent_id)
        if not agent:
            task.status = "failed"
            return {"status": "failed", "error": "Agent not found"}

        task.status = "running"
        task.started_at = datetime.now()

        # Simulate task execution
        await asyncio.sleep(random.uniform(0.01, 0.1))

        # Determine success based on agent capabilities
        avg_capability = sum(c.level for c in agent.capabilities.values()) / max(1, len(agent.capabilities))
        success = random.random() < (avg_capability * 0.9 + 0.1)

        if success:
            task.status = "completed"
            task.result = {"success": True, "output": f"Task {task_id} completed successfully"}
            agent.completed_tasks += 1

            # Update agent success rate
            total = agent.completed_tasks + 1
            agent.success_rate = (agent.success_rate * (total - 1) + 1.0) / total

            # Gain experience
            for cap in agent.capabilities.values():
                cap.experience += 1
                cap.level = min(1.0, cap.level + 0.01)  # Small improvement
        else:
            task.status = "failed"
            task.result = {"success": False, "error": "Task execution failed"}

            # Update success rate
            total = agent.completed_tasks + 1
            agent.success_rate = (agent.success_rate * (total - 1)) / total

        task.completed_at = datetime.now()

        # Remove from current tasks
        if task.id in agent.current_tasks:
            agent.current_tasks.remove(task.id)

        if not agent.current_tasks:
            agent.state = AgentState.IDLE

        return task.result

    async def broadcast_task(
        self,
        description: str,
        agent_type: Optional[AgentType] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """Broadcast a task to all matching agents."""
        matching_agents = [
            a for a in self.agents.values()
            if a.state != AgentState.TERMINATED
            and (agent_type is None or a.type == agent_type)
        ]

        tasks = []
        for agent in matching_agents:
            task = await self.assign_task(agent.id, description, parameters)
            tasks.append(task)

        return tasks

    # -------------------------------------------------------------------------
    # AGENT COMMUNICATION
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        content: Any
    ) -> AgentMessage:
        """Send a message between agents."""
        message = AgentMessage(
            id=self._gen_id("msg"),
            from_agent=from_agent_id,
            to_agent=to_agent_id,
            content=content,
            timestamp=datetime.now()
        )

        self.messages.append(message)
        return message

    async def broadcast_message(
        self,
        from_agent_id: str,
        content: Any,
        agent_type: Optional[AgentType] = None
    ) -> List[AgentMessage]:
        """Broadcast a message to all agents."""
        messages = []

        for agent in self.agents.values():
            if agent.id != from_agent_id:
                if agent_type is None or agent.type == agent_type:
                    msg = await self.send_message(from_agent_id, agent.id, content)
                    messages.append(msg)

        return messages

    # -------------------------------------------------------------------------
    # AGENT HIERARCHY
    # -------------------------------------------------------------------------

    async def create_hierarchy(
        self,
        leader_id: str,
        subordinate_ids: List[str]
    ) -> Dict[str, List[str]]:
        """Create a hierarchical structure of agents."""
        leader = self.agents.get(leader_id)
        if not leader:
            raise ValueError(f"Leader agent not found: {leader_id}")

        for sub_id in subordinate_ids:
            sub = self.agents.get(sub_id)
            if sub:
                sub.parent_id = leader_id
                if sub_id not in leader.children_ids:
                    leader.children_ids.append(sub_id)

        self.agent_hierarchy[leader_id] = subordinate_ids
        return self.agent_hierarchy

    async def get_hierarchy(self, root_id: str) -> Dict[str, Any]:
        """Get the hierarchy tree starting from an agent."""
        agent = self.agents.get(root_id)
        if not agent:
            return {}

        def build_tree(agent_id: str) -> Dict[str, Any]:
            a = self.agents.get(agent_id)
            if not a:
                return {}

            return {
                "id": a.id,
                "name": a.name,
                "type": a.type.value,
                "children": [build_tree(c) for c in a.children_ids]
            }

        return build_tree(root_id)

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _calculate_fitness(self, agent: SubAgent) -> float:
        """Calculate fitness score for an agent."""
        cap_score = sum(c.level for c in agent.capabilities.values()) / max(1, len(agent.capabilities))
        spec_score = agent.specialization_level.value / 7
        success_score = agent.success_rate

        return (cap_score * 0.4 + spec_score * 0.3 + success_score * 0.3)

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> List[SubAgent]:
        """Get all agents of a type."""
        return [a for a in self.agents.values() if a.type == agent_type]

    def get_available_agents(self) -> List[SubAgent]:
        """Get all idle agents."""
        return [a for a in self.agents.values() if a.state == AgentState.IDLE]

    def get_stats(self) -> Dict[str, Any]:
        """Get factory statistics."""
        agents = list(self.agents.values())
        return {
            "total_agents": len(agents),
            "agents_by_type": {t.value: len([a for a in agents if a.type == t]) for t in AgentType},
            "agents_by_state": {s.value: len([a for a in agents if a.state == s]) for s in AgentState},
            "total_tasks": len(self.tasks),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "completed"]),
            "total_messages": len(self.messages),
            "evolutions": len(self.evolutions),
            "templates_available": list(self.agent_templates.keys())
        }


# ============================================================================
# SINGLETON
# ============================================================================

_agent_factory: Optional[SubAgentFactory] = None


def get_agent_factory() -> SubAgentFactory:
    """Get the global agent factory."""
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = SubAgentFactory()
    return _agent_factory


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate agent factory."""
    print("=" * 60)
    print("🤖 SUB-AGENT FACTORY 🤖")
    print("=" * 60)

    factory = get_agent_factory()

    # Create agents from templates
    print("\n--- Creating Agents ---")
    researcher = await factory.create_from_template("researcher", "Alpha Researcher")
    executor = await factory.create_from_template("executor", "Beta Executor")
    hunter = await factory.create_from_template("hunter", "Gamma Hunter")

    print(f"Created: {researcher.name}, {executor.name}, {hunter.name}")

    # Create agent army
    print("\n--- Creating Agent Army ---")
    army = await factory.create_agent_army("executor", 5, "Soldier")
    print(f"Created army of {len(army)} agents")

    # Clone and evolve
    print("\n--- Evolution ---")
    clone = await factory.clone_agent(researcher.id)
    print(f"Cloned: {clone.name}")

    evolved = await factory.evolve_agent(researcher.id)
    print(f"Evolved: {evolved.name}, Specialization: {evolved.specialization_level.name}")

    # Fuse agents
    print("\n--- Fusion ---")
    fused = await factory.fuse_agents([researcher.id, executor.id], "Super Agent")
    print(f"Fused: {fused.name} with {len(fused.capabilities)} capabilities")

    # Task execution
    print("\n--- Task Execution ---")
    task = await factory.assign_task(researcher.id, "Research competition")
    result = await factory.execute_task(task.id)
    print(f"Task result: {result}")

    # Stats
    print("\n--- Statistics ---")
    stats = factory.get_stats()
    print(f"Total agents: {stats['total_agents']}")
    print(f"Completed tasks: {stats['completed_tasks']}")

    print("\n" + "=" * 60)
    print("🤖 FACTORY OPERATIONAL 🤖")


if __name__ == "__main__":
    asyncio.run(demo())
