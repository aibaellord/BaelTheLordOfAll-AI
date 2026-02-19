"""
Autonomous Agent Factory - Creates and Manages All Autonomous Agents
======================================================================

The factory that births specialized autonomous agents, each designed
for maximum capability in their domain.

"From the forge of creation, agents arise with singular purpose." — Ba'el
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
import uuid


logger = logging.getLogger("BAEL.AutonomousAgents")


# =============================================================================
# ENUMS - Agent Types and Capabilities
# =============================================================================

class AgentType(Enum):
    """Types of autonomous agents available."""
    # Code & Architecture
    CODE_ARCHITECT = "code_architect"
    REFACTORING = "refactoring"
    CODE_REVIEWER = "code_reviewer"

    # Security & Compliance
    SECURITY_AUDITOR = "security_auditor"
    COMPLIANCE = "compliance"

    # Performance & Optimization
    PERFORMANCE_OPTIMIZER = "performance_optimizer"
    DATABASE_OPTIMIZER = "database_optimizer"
    COST_OPTIMIZER = "cost_optimizer"

    # Testing & Quality
    TEST_GENERATOR = "test_generator"
    ERROR_HUNTER = "error_hunter"

    # Documentation & Communication
    DOCUMENTATION_GENERATOR = "documentation_generator"

    # Infrastructure & DevOps
    DEVOPS_AUTOMATION = "devops_automation"
    MONITORING = "monitoring"
    SCALING = "scaling"
    MIGRATION = "migration"

    # Integration & API
    API_DESIGNER = "api_designer"
    INTEGRATION = "integration"
    DEPENDENCY_ANALYZER = "dependency_analyzer"

    # Frontend & UI
    FRONTEND_GENIUS = "frontend_genius"

    # Innovation
    INNOVATION = "innovation"

    # Meta
    ORCHESTRATOR = "orchestrator"
    SUPERVISOR = "supervisor"


class AgentCapability(Enum):
    """Capabilities an agent can have."""
    # Analysis
    CODE_ANALYSIS = "code_analysis"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    COST_ANALYSIS = "cost_analysis"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"

    # Generation
    CODE_GENERATION = "code_generation"
    TEST_GENERATION = "test_generation"
    DOC_GENERATION = "doc_generation"
    CONFIG_GENERATION = "config_generation"

    # Modification
    CODE_MODIFICATION = "code_modification"
    REFACTORING = "refactoring"
    OPTIMIZATION = "optimization"

    # Execution
    COMMAND_EXECUTION = "command_execution"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    MONITORING = "monitoring"

    # Communication
    REPORTING = "reporting"
    ALERTING = "alerting"
    COLLABORATION = "collaboration"

    # Learning
    PATTERN_LEARNING = "pattern_learning"
    SELF_IMPROVEMENT = "self_improvement"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"


class AgentPriority(Enum):
    """Priority levels for agents."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class AgentStatus(Enum):
    """Status of an agent."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentMode(Enum):
    """Operating mode for agents."""
    AUTONOMOUS = "autonomous"      # Full autonomy
    SUPERVISED = "supervised"      # Human approval needed
    ADVISORY = "advisory"          # Suggestions only
    COLLABORATIVE = "collaborative"  # Works with other agents
    LEARNING = "learning"          # Learning mode


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class AgentConfig:
    """Configuration for an autonomous agent."""
    agent_type: AgentType
    name: str
    priority: AgentPriority = AgentPriority.MEDIUM
    mode: AgentMode = AgentMode.AUTONOMOUS
    capabilities: List[AgentCapability] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 3600
    retry_count: int = 3
    learning_enabled: bool = True
    collaboration_enabled: bool = True
    auto_report: bool = True
    sacred_alignment: float = 0.618  # Golden ratio inverse


@dataclass
class AgentTask:
    """A task for an agent to execute."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: AgentPriority = AgentPriority.MEDIUM
    target_path: Optional[Path] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: AgentStatus = AgentStatus.IDLE


@dataclass
class AgentResult:
    """Result from an agent's work."""
    task_id: str
    agent_id: str
    agent_type: AgentType
    success: bool
    result: Any = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    changes_made: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration_ms: int = 0
    average_duration_ms: float = 0.0
    success_rate: float = 0.0
    last_active: Optional[datetime] = None
    improvements_made: int = 0
    issues_found: int = 0
    code_generated_lines: int = 0
    code_modified_lines: int = 0


# =============================================================================
# BASE AGENT CLASS
# =============================================================================

class AutonomousAgent(ABC):
    """Base class for all autonomous agents."""

    def __init__(self, config: AgentConfig):
        self.id = str(uuid.uuid4())
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self.metrics = AgentMetrics()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.current_tasks: Dict[str, AgentTask] = {}
        self.completed_results: List[AgentResult] = []
        self.knowledge_base: Dict[str, Any] = {}
        self._running = False
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def agent_type(self) -> AgentType:
        return self.config.agent_type

    async def initialize(self) -> None:
        """Initialize the agent."""
        logger.info(f"Initializing {self.name} ({self.agent_type.value})")
        await self._setup()
        self.status = AgentStatus.IDLE

    @abstractmethod
    async def _setup(self) -> None:
        """Agent-specific setup."""
        pass

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a specific task."""
        pass

    async def start(self) -> None:
        """Start the agent's main loop."""
        self._running = True
        logger.info(f"{self.name} started")

        while self._running:
            try:
                # Get next task
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )

                # Execute task
                self.status = AgentStatus.WORKING
                self.current_tasks[task.id] = task

                start_time = datetime.now()
                try:
                    result = await self.execute_task(task)
                    self.metrics.tasks_completed += 1
                except Exception as e:
                    result = AgentResult(
                        task_id=task.id,
                        agent_id=self.id,
                        agent_type=self.agent_type,
                        success=False,
                        error=str(e)
                    )
                    self.metrics.tasks_failed += 1

                duration = (datetime.now() - start_time).total_seconds() * 1000
                result.duration_ms = int(duration)
                self.metrics.total_duration_ms += int(duration)

                # Update metrics
                total = self.metrics.tasks_completed + self.metrics.tasks_failed
                if total > 0:
                    self.metrics.average_duration_ms = self.metrics.total_duration_ms / total
                    self.metrics.success_rate = self.metrics.tasks_completed / total

                self.metrics.last_active = datetime.now()
                self.completed_results.append(result)

                # Remove from current
                del self.current_tasks[task.id]

                # Learn from result if enabled
                if self.config.learning_enabled:
                    await self._learn_from_result(result)

                self.status = AgentStatus.IDLE

            except asyncio.TimeoutError:
                # No task available, continue waiting
                continue
            except Exception as e:
                logger.error(f"{self.name} error: {e}")
                self.status = AgentStatus.FAILED

    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False
        self.status = AgentStatus.TERMINATED
        logger.info(f"{self.name} stopped")

    async def submit_task(self, task: AgentTask) -> str:
        """Submit a task to the agent."""
        await self.task_queue.put(task)
        return task.id

    async def _learn_from_result(self, result: AgentResult) -> None:
        """Learn from a task result for self-improvement."""
        # Store patterns in knowledge base
        pattern_key = f"{result.task_id[:8]}_pattern"
        self.knowledge_base[pattern_key] = {
            "success": result.success,
            "duration": result.duration_ms,
            "metrics": result.metrics,
            "timestamp": datetime.now()
        }

    def get_status_report(self) -> Dict[str, Any]:
        """Get a status report for this agent."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "status": self.status.value,
            "mode": self.config.mode.value,
            "priority": self.config.priority.value,
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "success_rate": f"{self.metrics.success_rate:.1%}",
                "avg_duration_ms": self.metrics.average_duration_ms,
                "improvements_made": self.metrics.improvements_made,
                "issues_found": self.metrics.issues_found,
            },
            "current_tasks": len(self.current_tasks),
            "queued_tasks": self.task_queue.qsize(),
        }


# =============================================================================
# AGENT FACTORY
# =============================================================================

class AutonomousAgentFactory:
    """Factory for creating and managing autonomous agents."""

    _instance = None
    _agents: Dict[str, AutonomousAgent] = {}
    _agent_types: Dict[AgentType, Type[AutonomousAgent]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_agent_type(
        cls,
        agent_type: AgentType,
        agent_class: Type[AutonomousAgent]
    ) -> None:
        """Register an agent type with its implementation class."""
        cls._agent_types[agent_type] = agent_class
        logger.debug(f"Registered agent type: {agent_type.value}")

    @classmethod
    async def create_agent(
        cls,
        agent_type: AgentType,
        name: Optional[str] = None,
        config: Optional[AgentConfig] = None
    ) -> AutonomousAgent:
        """Create a new autonomous agent."""
        if agent_type not in cls._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = cls._agent_types[agent_type]

        if config is None:
            config = AgentConfig(
                agent_type=agent_type,
                name=name or f"{agent_type.value}_agent",
            )

        agent = agent_class(config)
        await agent.initialize()

        cls._agents[agent.id] = agent
        logger.info(f"Created agent: {agent.name} (ID: {agent.id})")

        return agent

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[AutonomousAgent]:
        """Get an agent by ID."""
        return cls._agents.get(agent_id)

    @classmethod
    def get_agents_by_type(cls, agent_type: AgentType) -> List[AutonomousAgent]:
        """Get all agents of a specific type."""
        return [
            agent for agent in cls._agents.values()
            if agent.agent_type == agent_type
        ]

    @classmethod
    def get_all_agents(cls) -> List[AutonomousAgent]:
        """Get all agents."""
        return list(cls._agents.values())

    @classmethod
    async def deploy_team(
        cls,
        agent_types: List[AgentType],
        target: Path
    ) -> List[AutonomousAgent]:
        """Deploy a team of agents for a specific target."""
        team = []
        for agent_type in agent_types:
            agent = await cls.create_agent(agent_type)
            team.append(agent)

        logger.info(f"Deployed team of {len(team)} agents for {target}")
        return team

    @classmethod
    def get_factory_status(cls) -> Dict[str, Any]:
        """Get status of the entire factory."""
        return {
            "total_agents": len(cls._agents),
            "registered_types": len(cls._agent_types),
            "agents_by_type": {
                agent_type.value: len(cls.get_agents_by_type(agent_type))
                for agent_type in AgentType
                if cls.get_agents_by_type(agent_type)
            },
            "agents_by_status": {
                status.value: len([
                    a for a in cls._agents.values()
                    if a.status == status
                ])
                for status in AgentStatus
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def create_agent(
    agent_type: AgentType,
    name: Optional[str] = None
) -> AutonomousAgent:
    """Convenience function to create an agent."""
    return await AutonomousAgentFactory.create_agent(agent_type, name)


async def deploy_agent_team(
    agent_types: List[AgentType],
    target: Path
) -> List[AutonomousAgent]:
    """Convenience function to deploy a team of agents."""
    return await AutonomousAgentFactory.deploy_team(agent_types, target)


# =============================================================================
# AGENT DECORATOR
# =============================================================================

def autonomous_agent(agent_type: AgentType):
    """Decorator to register an agent class."""
    def decorator(cls: Type[AutonomousAgent]) -> Type[AutonomousAgent]:
        AutonomousAgentFactory.register_agent_type(agent_type, cls)
        return cls
    return decorator
