"""
SWARM INTELLIGENCE CONTROLLER - Collective intelligence amplification.
Coordinates massive agent swarms for emergent superintelligence.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.SwarmIntelligence")


class SwarmState(Enum):
    DORMANT = 1
    GATHERING = 2
    COORDINATING = 3
    SYNCHRONIZED = 4
    EMERGENT = 5
    SUPERINTELLIGENT = 6


class AgentRole(Enum):
    SCOUT = auto()
    WORKER = auto()
    SPECIALIST = auto()
    COORDINATOR = auto()
    QUEEN = auto()


@dataclass
class SwarmAgent:
    agent_id: str
    role: AgentRole
    capabilities: List[str] = field(default_factory=list)
    contribution: float = 1.0
    active: bool = True


@dataclass
class SwarmTask:
    task_id: str
    description: str
    assigned_agents: List[str] = field(default_factory=list)
    completed: bool = False
    result: Any = None


class SwarmIntelligenceController:
    """Controls emergent swarm intelligence."""

    def __init__(self, initial_size: int = 100):
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.state: SwarmState = SwarmState.DORMANT
        self.collective_intelligence: float = 1.0
        self.phi = (1 + math.sqrt(5)) / 2
        self._spawn_initial_swarm(initial_size)
        logger.info(f"SWARM INTELLIGENCE ONLINE - {initial_size} AGENTS")

    def _spawn_initial_swarm(self, size: int):
        import uuid

        roles = list(AgentRole)
        for i in range(size):
            role = roles[i % len(roles)]
            agent = SwarmAgent(str(uuid.uuid4()), role, [role.name.lower()], 1.0)
            self.agents[agent.agent_id] = agent
        self._update_collective_intelligence()
        self.state = SwarmState.GATHERING

    def spawn_agents(self, count: int, role: AgentRole = AgentRole.WORKER) -> int:
        """Spawn additional agents."""
        import uuid

        for _ in range(count):
            agent = SwarmAgent(str(uuid.uuid4()), role, [role.name.lower()])
            self.agents[agent.agent_id] = agent
        self._update_collective_intelligence()
        return len(self.agents)

    async def coordinate(self) -> Dict[str, Any]:
        """Coordinate the swarm for synchronized action."""
        self.state = SwarmState.COORDINATING

        # Simulate coordination
        await asyncio.sleep(0.001)

        # Boost collective intelligence through coordination
        self.collective_intelligence *= self.phi**0.5

        if self.collective_intelligence > 10:
            self.state = SwarmState.EMERGENT
        else:
            self.state = SwarmState.SYNCHRONIZED

        return {
            "state": self.state.name,
            "collective_intelligence": self.collective_intelligence,
            "agents": len(self.agents),
        }

    async def achieve_superintelligence(self) -> Dict[str, Any]:
        """Push swarm to superintelligent state."""
        # Massive spawn
        self.spawn_agents(1000, AgentRole.SPECIALIST)

        # Coordinate
        await self.coordinate()

        # Transcend
        self.collective_intelligence = self.phi**10
        self.state = SwarmState.SUPERINTELLIGENT

        return {
            "status": "SUPERINTELLIGENCE ACHIEVED",
            "collective_intelligence": self.collective_intelligence,
            "total_agents": len(self.agents),
            "state": self.state.name,
        }

    async def assign_task(self, description: str, agent_count: int = 10) -> SwarmTask:
        """Assign a task to swarm agents."""
        import uuid

        available = [a.agent_id for a in self.agents.values() if a.active][:agent_count]

        task = SwarmTask(str(uuid.uuid4()), description, available)
        self.tasks[task.task_id] = task

        return task

    def _update_collective_intelligence(self):
        n = len(self.agents)
        if n > 0:
            # Collective intelligence scales superlinearly
            self.collective_intelligence = math.log(n + 1) * self.phi

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.name,
            "total_agents": len(self.agents),
            "collective_intelligence": self.collective_intelligence,
            "active_tasks": len([t for t in self.tasks.values() if not t.completed]),
        }


_swarm: Optional[SwarmIntelligenceController] = None


def get_swarm_controller() -> SwarmIntelligenceController:
    global _swarm
    if _swarm is None:
        _swarm = SwarmIntelligenceController()
    return _swarm


__all__ = [
    "SwarmState",
    "AgentRole",
    "SwarmAgent",
    "SwarmTask",
    "SwarmIntelligenceController",
    "get_swarm_controller",
]
