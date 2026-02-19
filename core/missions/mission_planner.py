"""
BAEL Mission Planner
=====================

Strategic mission planning and orchestration.
Creates comprehensive plans for complex objectives.

Features:
- Mission creation and management
- Resource allocation
- Timeline planning
- Risk assessment
- Dependency mapping
- Constraint handling
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MissionStatus(Enum):
    """Mission status."""
    DRAFT = "draft"
    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionPriority(Enum):
    """Mission priority levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    BACKGROUND = 1


class MissionType(Enum):
    """Types of missions."""
    RESEARCH = "research"
    DEVELOPMENT = "development"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    SECURITY = "security"
    DATA_COLLECTION = "data_collection"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    CUSTOM = "custom"


@dataclass
class Resource:
    """Resource required for mission."""
    type: str  # api_key, compute, storage, network, tool
    name: str
    required: bool = True
    allocated: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    """Mission constraint."""
    type: str  # time, cost, resource, dependency
    description: str
    value: Any = None
    is_hard: bool = True  # Hard constraint cannot be violated


@dataclass
class RiskFactor:
    """Risk factor for mission."""
    name: str
    probability: float  # 0-1
    impact: float  # 0-1
    mitigation: Optional[str] = None

    @property
    def score(self) -> float:
        return self.probability * self.impact


@dataclass
class MissionPhase:
    """Phase within a mission."""
    id: str
    name: str
    description: str = ""

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Timing
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: MissionStatus = MissionStatus.DRAFT
    progress: float = 0.0

    # Tasks
    task_ids: List[str] = field(default_factory=list)


@dataclass
class MissionConfig:
    """Mission configuration."""
    # Execution
    max_retries: int = 3
    retry_delay_seconds: float = 60.0
    timeout_seconds: Optional[float] = None

    # Parallelism
    max_parallel_tasks: int = 5
    max_parallel_phases: int = 2

    # Monitoring
    checkpoint_interval_seconds: float = 300.0
    progress_report_interval_seconds: float = 60.0

    # Failure handling
    fail_fast: bool = False
    continue_on_phase_failure: bool = True

    # Resources
    max_api_calls_per_minute: int = 100
    max_cost_budget: float = 0.0  # 0 = unlimited


@dataclass
class Mission:
    """A complete mission definition."""
    id: str
    name: str
    description: str = ""

    # Classification
    type: MissionType = MissionType.CUSTOM
    priority: MissionPriority = MissionPriority.MEDIUM

    # Phases
    phases: List[MissionPhase] = field(default_factory=list)

    # Resources and constraints
    resources: List[Resource] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    # Risk assessment
    risks: List[RiskFactor] = field(default_factory=list)

    # Configuration
    config: MissionConfig = field(default_factory=MissionConfig)

    # Status
    status: MissionStatus = MissionStatus.DRAFT
    progress: float = 0.0

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status in {MissionStatus.IN_PROGRESS, MissionStatus.PAUSED}

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            MissionStatus.COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        }

    @property
    def risk_score(self) -> float:
        if not self.risks:
            return 0.0
        return sum(r.score for r in self.risks) / len(self.risks)


class MissionPlanner:
    """
    Strategic mission planner for BAEL.
    """

    def __init__(self):
        # Mission storage
        self.missions: Dict[str, Mission] = {}
        self.active_missions: Set[str] = set()

        # Planning callbacks
        self._planners: Dict[MissionType, Callable] = {}

        # Stats
        self.stats = {
            "missions_created": 0,
            "missions_completed": 0,
            "missions_failed": 0,
            "total_planning_time_ms": 0.0,
        }

        # Register default planners
        self._register_default_planners()

    def _register_default_planners(self) -> None:
        """Register default mission planners."""
        self._planners[MissionType.RESEARCH] = self._plan_research_mission
        self._planners[MissionType.DEVELOPMENT] = self._plan_development_mission
        self._planners[MissionType.ANALYSIS] = self._plan_analysis_mission
        self._planners[MissionType.AUTOMATION] = self._plan_automation_mission
        self._planners[MissionType.SECURITY] = self._plan_security_mission

    def _generate_id(self, name: str) -> str:
        """Generate mission ID."""
        timestamp = str(time.time())
        hash_input = f"{name}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def create_mission(
        self,
        name: str,
        description: str = "",
        mission_type: MissionType = MissionType.CUSTOM,
        priority: MissionPriority = MissionPriority.MEDIUM,
        config: Optional[MissionConfig] = None,
        **kwargs,
    ) -> Mission:
        """
        Create a new mission.

        Args:
            name: Mission name
            description: Mission description
            mission_type: Type of mission
            priority: Mission priority
            config: Mission configuration
            **kwargs: Additional mission attributes

        Returns:
            Created Mission
        """
        self.stats["missions_created"] += 1

        mission_id = self._generate_id(name)

        mission = Mission(
            id=mission_id,
            name=name,
            description=description,
            type=mission_type,
            priority=priority,
            config=config or MissionConfig(),
            **kwargs,
        )

        self.missions[mission_id] = mission
        logger.info(f"Created mission: {name} ({mission_id})")

        return mission

    async def plan_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> Mission:
        """
        Plan a mission based on objectives.

        Args:
            mission: Mission to plan
            objectives: List of objective descriptions

        Returns:
            Planned mission with phases
        """
        start_time = time.monotonic()

        # Get type-specific planner
        planner = self._planners.get(
            mission.type,
            self._plan_generic_mission,
        )

        try:
            # Generate phases
            phases = await planner(mission, objectives)
            mission.phases = phases

            # Assess resources
            mission.resources = self._assess_resources(mission)

            # Identify constraints
            mission.constraints = self._identify_constraints(mission)

            # Assess risks
            mission.risks = self._assess_risks(mission)

            # Estimate timeline
            mission.estimated_completion = self._estimate_completion(mission)

            # Update status
            mission.status = MissionStatus.PLANNED

            elapsed = (time.monotonic() - start_time) * 1000
            self.stats["total_planning_time_ms"] += elapsed

            logger.info(f"Planned mission {mission.id}: {len(phases)} phases")

        except Exception as e:
            logger.error(f"Mission planning error: {e}")
            mission.errors.append(f"Planning error: {e}")

        return mission

    async def _plan_generic_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Generic mission planner."""
        phases = []

        # Phase 1: Initialization
        phases.append(MissionPhase(
            id=f"{mission.id}_init",
            name="Initialization",
            description="Set up resources and validate requirements",
            estimated_duration=timedelta(minutes=5),
        ))

        # Phase 2: Main execution for each objective
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_obj_{i}",
                name=f"Objective {i+1}",
                description=objective,
                depends_on=[phases[-1].id] if phases else [],
                estimated_duration=timedelta(hours=1),
            ))

        # Phase 3: Finalization
        phases.append(MissionPhase(
            id=f"{mission.id}_final",
            name="Finalization",
            description="Consolidate results and clean up",
            depends_on=[phases[-1].id] if phases else [],
            estimated_duration=timedelta(minutes=10),
        ))

        return phases

    async def _plan_research_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Plan research mission."""
        phases = []

        # Discovery phase
        phases.append(MissionPhase(
            id=f"{mission.id}_discovery",
            name="Discovery",
            description="Gather initial information and identify sources",
            estimated_duration=timedelta(hours=2),
        ))

        # Deep research phases
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_research_{i}",
                name=f"Research: {objective[:30]}...",
                description=f"Deep research on: {objective}",
                depends_on=[f"{mission.id}_discovery"],
                estimated_duration=timedelta(hours=3),
            ))

        # Synthesis phase
        research_phase_ids = [p.id for p in phases if "research" in p.id]
        phases.append(MissionPhase(
            id=f"{mission.id}_synthesis",
            name="Synthesis",
            description="Synthesize findings and draw conclusions",
            depends_on=research_phase_ids,
            estimated_duration=timedelta(hours=1),
        ))

        # Report phase
        phases.append(MissionPhase(
            id=f"{mission.id}_report",
            name="Report Generation",
            description="Generate comprehensive research report",
            depends_on=[f"{mission.id}_synthesis"],
            estimated_duration=timedelta(minutes=30),
        ))

        return phases

    async def _plan_development_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Plan development mission."""
        phases = []

        # Analysis phase
        phases.append(MissionPhase(
            id=f"{mission.id}_analysis",
            name="Requirements Analysis",
            description="Analyze requirements and design solution",
            estimated_duration=timedelta(hours=2),
        ))

        # Implementation phases
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_impl_{i}",
                name=f"Implement: {objective[:25]}...",
                description=f"Implement: {objective}",
                depends_on=[f"{mission.id}_analysis"],
                estimated_duration=timedelta(hours=4),
            ))

        # Integration phase
        impl_phase_ids = [p.id for p in phases if "impl" in p.id]
        phases.append(MissionPhase(
            id=f"{mission.id}_integration",
            name="Integration",
            description="Integrate all components",
            depends_on=impl_phase_ids,
            estimated_duration=timedelta(hours=2),
        ))

        # Testing phase
        phases.append(MissionPhase(
            id=f"{mission.id}_testing",
            name="Testing",
            description="Comprehensive testing and validation",
            depends_on=[f"{mission.id}_integration"],
            estimated_duration=timedelta(hours=2),
        ))

        # Deployment phase
        phases.append(MissionPhase(
            id=f"{mission.id}_deployment",
            name="Deployment",
            description="Deploy and verify",
            depends_on=[f"{mission.id}_testing"],
            estimated_duration=timedelta(hours=1),
        ))

        return phases

    async def _plan_analysis_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Plan analysis mission."""
        phases = []

        # Data collection
        phases.append(MissionPhase(
            id=f"{mission.id}_collection",
            name="Data Collection",
            description="Collect and prepare data for analysis",
            estimated_duration=timedelta(hours=2),
        ))

        # Analysis phases
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_analyze_{i}",
                name=f"Analyze: {objective[:25]}...",
                description=f"Analyze: {objective}",
                depends_on=[f"{mission.id}_collection"],
                estimated_duration=timedelta(hours=2),
            ))

        # Correlation
        analyze_ids = [p.id for p in phases if "analyze" in p.id]
        phases.append(MissionPhase(
            id=f"{mission.id}_correlation",
            name="Correlation Analysis",
            description="Find correlations and patterns",
            depends_on=analyze_ids,
            estimated_duration=timedelta(hours=1),
        ))

        # Insights
        phases.append(MissionPhase(
            id=f"{mission.id}_insights",
            name="Insight Generation",
            description="Generate actionable insights",
            depends_on=[f"{mission.id}_correlation"],
            estimated_duration=timedelta(hours=1),
        ))

        return phases

    async def _plan_automation_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Plan automation mission."""
        phases = []

        # Process mapping
        phases.append(MissionPhase(
            id=f"{mission.id}_mapping",
            name="Process Mapping",
            description="Map current processes and identify automation points",
            estimated_duration=timedelta(hours=2),
        ))

        # Automation implementation
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_automate_{i}",
                name=f"Automate: {objective[:25]}...",
                description=f"Automate: {objective}",
                depends_on=[f"{mission.id}_mapping"],
                estimated_duration=timedelta(hours=3),
            ))

        # Integration
        auto_ids = [p.id for p in phases if "automate" in p.id]
        phases.append(MissionPhase(
            id=f"{mission.id}_integrate",
            name="Workflow Integration",
            description="Integrate automated components",
            depends_on=auto_ids,
            estimated_duration=timedelta(hours=2),
        ))

        # Monitoring setup
        phases.append(MissionPhase(
            id=f"{mission.id}_monitoring",
            name="Monitoring Setup",
            description="Set up monitoring and alerting",
            depends_on=[f"{mission.id}_integrate"],
            estimated_duration=timedelta(hours=1),
        ))

        return phases

    async def _plan_security_mission(
        self,
        mission: Mission,
        objectives: List[str],
    ) -> List[MissionPhase]:
        """Plan security mission."""
        phases = []

        # Reconnaissance
        phases.append(MissionPhase(
            id=f"{mission.id}_recon",
            name="Reconnaissance",
            description="Gather information about target",
            estimated_duration=timedelta(hours=2),
        ))

        # Vulnerability scanning
        phases.append(MissionPhase(
            id=f"{mission.id}_scanning",
            name="Vulnerability Scanning",
            description="Scan for vulnerabilities",
            depends_on=[f"{mission.id}_recon"],
            estimated_duration=timedelta(hours=3),
        ))

        # Assessment phases
        for i, objective in enumerate(objectives):
            phases.append(MissionPhase(
                id=f"{mission.id}_assess_{i}",
                name=f"Assess: {objective[:25]}...",
                description=f"Security assessment: {objective}",
                depends_on=[f"{mission.id}_scanning"],
                estimated_duration=timedelta(hours=2),
            ))

        # Report
        assess_ids = [p.id for p in phases if "assess" in p.id]
        phases.append(MissionPhase(
            id=f"{mission.id}_report",
            name="Security Report",
            description="Generate security assessment report",
            depends_on=assess_ids,
            estimated_duration=timedelta(hours=1),
        ))

        return phases

    def _assess_resources(self, mission: Mission) -> List[Resource]:
        """Assess required resources for mission."""
        resources = []

        # API resources based on mission type
        if mission.type in {MissionType.RESEARCH, MissionType.ANALYSIS}:
            resources.append(Resource(
                type="api_key",
                name="LLM API",
                required=True,
            ))
            resources.append(Resource(
                type="api_key",
                name="Search API",
                required=False,
            ))

        if mission.type == MissionType.DEVELOPMENT:
            resources.append(Resource(
                type="tool",
                name="Code Generator",
                required=True,
            ))

        if mission.type == MissionType.SECURITY:
            resources.append(Resource(
                type="tool",
                name="Security Scanner",
                required=True,
            ))

        # Compute resources
        resources.append(Resource(
            type="compute",
            name="Execution Environment",
            required=True,
            details={"min_memory_gb": 4},
        ))

        return resources

    def _identify_constraints(self, mission: Mission) -> List[Constraint]:
        """Identify mission constraints."""
        constraints = []

        # Time constraints
        if mission.config.timeout_seconds:
            constraints.append(Constraint(
                type="time",
                description=f"Must complete within {mission.config.timeout_seconds}s",
                value=mission.config.timeout_seconds,
                is_hard=True,
            ))

        # Cost constraints
        if mission.config.max_cost_budget > 0:
            constraints.append(Constraint(
                type="cost",
                description=f"Budget limit: ${mission.config.max_cost_budget}",
                value=mission.config.max_cost_budget,
                is_hard=True,
            ))

        # Rate limiting
        constraints.append(Constraint(
            type="resource",
            description=f"Max {mission.config.max_api_calls_per_minute} API calls/min",
            value=mission.config.max_api_calls_per_minute,
            is_hard=True,
        ))

        return constraints

    def _assess_risks(self, mission: Mission) -> List[RiskFactor]:
        """Assess mission risks."""
        risks = []

        # API failure risk
        risks.append(RiskFactor(
            name="API Unavailability",
            probability=0.1,
            impact=0.8,
            mitigation="Use fallback providers",
        ))

        # Timeout risk
        if len(mission.phases) > 5:
            risks.append(RiskFactor(
                name="Execution Timeout",
                probability=0.2,
                impact=0.6,
                mitigation="Implement checkpointing",
            ))

        # Data quality risk
        if mission.type in {MissionType.RESEARCH, MissionType.ANALYSIS}:
            risks.append(RiskFactor(
                name="Data Quality Issues",
                probability=0.3,
                impact=0.5,
                mitigation="Implement validation",
            ))

        return risks

    def _estimate_completion(self, mission: Mission) -> datetime:
        """Estimate mission completion time."""
        total_duration = timedelta()

        # Sum phase durations (simplified, ignoring parallelism)
        for phase in mission.phases:
            total_duration += phase.estimated_duration

        # Add buffer
        buffer_factor = 1.2 + (mission.risk_score * 0.3)
        buffered_duration = total_duration * buffer_factor

        return datetime.now() + buffered_duration

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get mission by ID."""
        return self.missions.get(mission_id)

    def list_missions(
        self,
        status: Optional[MissionStatus] = None,
        mission_type: Optional[MissionType] = None,
    ) -> List[Mission]:
        """List missions with optional filtering."""
        missions = list(self.missions.values())

        if status:
            missions = [m for m in missions if m.status == status]

        if mission_type:
            missions = [m for m in missions if m.type == mission_type]

        return sorted(missions, key=lambda m: m.priority.value, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get planner statistics."""
        return {
            **self.stats,
            "total_missions": len(self.missions),
            "active_missions": len(self.active_missions),
        }


def demo():
    """Demonstrate mission planner."""
    import asyncio

    print("=" * 60)
    print("BAEL Mission Planner Demo")
    print("=" * 60)

    planner = MissionPlanner()

    # Create mission
    mission = planner.create_mission(
        name="Research AI Trends",
        description="Comprehensive research on AI industry trends",
        mission_type=MissionType.RESEARCH,
        priority=MissionPriority.HIGH,
    )

    print(f"\nCreated mission: {mission.name}")
    print(f"  ID: {mission.id}")
    print(f"  Type: {mission.type.value}")
    print(f"  Priority: {mission.priority.value}")

    # Plan mission
    async def plan():
        objectives = [
            "Analyze current LLM developments",
            "Research emerging AI frameworks",
            "Identify market trends",
        ]
        return await planner.plan_mission(mission, objectives)

    planned_mission = asyncio.run(plan())

    print(f"\nPlanned phases: {len(planned_mission.phases)}")
    for phase in planned_mission.phases:
        print(f"  • {phase.name}")

    print(f"\nResources: {len(planned_mission.resources)}")
    print(f"Risks: {len(planned_mission.risks)} (score: {planned_mission.risk_score:.2f})")
    print(f"Estimated completion: {planned_mission.estimated_completion}")

    print(f"\nStats: {planner.get_stats()}")


if __name__ == "__main__":
    demo()
