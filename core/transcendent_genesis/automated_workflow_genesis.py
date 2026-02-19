"""
BAEL - Automated Workflow Genesis
Revolutionary system for creating, optimizing, and evolving complex workflows.

This system can:
1. Generate workflows from natural language descriptions
2. Analyze GitHub repositories to extract optimal workflows
3. Compose micro-agents into workflow teams
4. Apply sacred geometry to workflow optimization
5. Self-evolve workflows based on execution feedback
6. Find and surpass competitor workflows
7. Create meta-workflows that orchestrate other workflows

Exceeds any workflow system in existence.
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import copy

logger = logging.getLogger("BAEL.AutomatedWorkflowGenesis")

# Sacred Mathematics
PHI = (1 + math.sqrt(5)) / 2
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


class WorkflowType(Enum):
    """Types of workflows."""
    LINEAR = "linear"           # Sequential steps
    PARALLEL = "parallel"       # Concurrent execution
    CONDITIONAL = "conditional"  # Branching logic
    LOOP = "loop"               # Iterative
    RECURSIVE = "recursive"     # Self-referential
    ADAPTIVE = "adaptive"       # Changes based on context
    EMERGENT = "emergent"       # Self-organizing
    TRANSCENDENT = "transcendent"  # Beyond normal patterns


class WorkflowPhase(Enum):
    """Phases of workflow execution."""
    INITIALIZATION = "initialization"
    PLANNING = "planning"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    ADAPTATION = "adaptation"
    COMPLETION = "completion"
    EVOLUTION = "evolution"


class AgentRole(Enum):
    """Roles for micro-agents in workflows."""
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    OPTIMIZER = "optimizer"
    EXPLORER = "explorer"
    SYNTHESIZER = "synthesizer"
    GUARDIAN = "guardian"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    step_id: str
    name: str
    description: str

    # Execution
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    # Configuration
    timeout_seconds: float = 300.0
    retries: int = 3
    can_parallelize: bool = True

    # Metrics
    avg_execution_time_ms: float = 0.0
    success_rate: float = 1.0

    # Sacred geometry weight
    golden_weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.step_id,
            "name": self.name,
            "action": self.action,
            "depends_on": self.depends_on,
            "outputs": self.outputs
        }


@dataclass
class MicroAgent:
    """A micro-agent that executes workflow steps."""
    agent_id: str
    name: str
    role: AgentRole

    # Capabilities
    skills: List[str] = field(default_factory=list)

    # State
    status: str = "idle"
    current_task: Optional[str] = None

    # Metrics
    tasks_completed: int = 0
    success_rate: float = 1.0

    # Psychological profile for optimization
    creativity: float = 0.5
    precision: float = 0.5
    speed: float = 0.5
    collaboration: float = 0.5


@dataclass
class Workflow:
    """A complete workflow definition."""
    workflow_id: str
    name: str
    description: str
    workflow_type: WorkflowType

    # Structure
    steps: List[WorkflowStep] = field(default_factory=list)
    agents: List[MicroAgent] = field(default_factory=list)

    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Evolution
    version: str = "1.0.0"
    parent_workflows: List[str] = field(default_factory=list)
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)

    # Metrics
    executions: int = 0
    successes: int = 0
    avg_duration_ms: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.successes / self.executions

    def get_fitness_score(self) -> float:
        """Calculate fitness for evolution."""
        success_weight = 1 / PHI
        speed_weight = 1 / (PHI ** 2)
        complexity_weight = 1 / (PHI ** 3)

        speed_score = 1.0 / (1.0 + self.avg_duration_ms / 10000)
        complexity_score = 1.0 / (1.0 + len(self.steps) / 10)

        return (
            self.success_rate * success_weight +
            speed_score * speed_weight +
            complexity_score * complexity_weight
        )


@dataclass
class WorkflowExecutionResult:
    """Result of workflow execution."""
    workflow_id: str
    success: bool

    # Outputs
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    duration_ms: float = 0.0
    steps_executed: int = 0
    steps_failed: int = 0

    # Insights
    bottlenecks: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)
    emergent_patterns: List[str] = field(default_factory=list)


class AutomatedWorkflowGenesis:
    """
    Automated Workflow Genesis - Creates and evolves workflows.

    Revolutionary capabilities:
    1. Natural Language Workflow Creation
    2. GitHub Repository Workflow Extraction
    3. Micro-Agent Team Composition
    4. Sacred Geometry Optimization
    5. Self-Evolving Workflows
    6. Competitive Workflow Analysis
    7. Meta-Workflow Orchestration
    """

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        enable_auto_evolution: bool = True
    ):
        self.llm_provider = llm_provider
        self.auto_evolution = enable_auto_evolution

        # Workflow registry
        self._workflows: Dict[str, Workflow] = {}

        # Agent pool
        self._agents: Dict[str, MicroAgent] = {}

        # Templates
        self._workflow_templates = self._create_templates()

        # Evolution
        self._evolution_pool: List[Workflow] = []

        # Statistics
        self._stats = {
            "workflows_created": 0,
            "workflows_executed": 0,
            "workflows_evolved": 0,
            "agents_spawned": 0
        }

        logger.info("AutomatedWorkflowGenesis initialized")

    def _create_templates(self) -> Dict[str, Dict[str, Any]]:
        """Create workflow templates."""
        return {
            "research": {
                "steps": [
                    {"action": "gather_sources", "outputs": ["sources"]},
                    {"action": "analyze_content", "depends_on": ["gather_sources"]},
                    {"action": "synthesize_insights", "depends_on": ["analyze_content"]},
                    {"action": "generate_report", "depends_on": ["synthesize_insights"]}
                ],
                "type": WorkflowType.LINEAR
            },
            "development": {
                "steps": [
                    {"action": "analyze_requirements", "outputs": ["specs"]},
                    {"action": "design_architecture", "depends_on": ["analyze_requirements"]},
                    {"action": "generate_code", "depends_on": ["design_architecture"]},
                    {"action": "write_tests", "depends_on": ["design_architecture"]},
                    {"action": "review_code", "depends_on": ["generate_code", "write_tests"]},
                    {"action": "deploy", "depends_on": ["review_code"]}
                ],
                "type": WorkflowType.CONDITIONAL
            },
            "analysis": {
                "steps": [
                    {"action": "collect_data", "outputs": ["data"]},
                    {"action": "preprocess", "depends_on": ["collect_data"]},
                    {"action": "analyze_patterns", "depends_on": ["preprocess"]},
                    {"action": "generate_insights", "depends_on": ["analyze_patterns"]},
                    {"action": "validate_findings", "depends_on": ["generate_insights"]}
                ],
                "type": WorkflowType.LINEAR
            },
            "automation": {
                "steps": [
                    {"action": "identify_task", "outputs": ["task_spec"]},
                    {"action": "create_agent", "depends_on": ["identify_task"]},
                    {"action": "configure_automation", "depends_on": ["create_agent"]},
                    {"action": "test_automation", "depends_on": ["configure_automation"]},
                    {"action": "deploy_automation", "depends_on": ["test_automation"]},
                    {"action": "monitor_performance", "depends_on": ["deploy_automation"]}
                ],
                "type": WorkflowType.ADAPTIVE
            }
        }

    async def create_workflow(
        self,
        description: str,
        workflow_type: WorkflowType = WorkflowType.ADAPTIVE,
        parameters: Dict[str, Any] = None
    ) -> Workflow:
        """
        Create a workflow from natural language description.
        """
        workflow_id = f"workflow_{hashlib.md5(f'{description}{time.time()}'.encode()).hexdigest()[:10]}"

        # Infer steps from description
        steps = await self._infer_steps(description, workflow_type)

        # Create optimal agent team
        agents = await self._compose_agent_team(steps)

        workflow = Workflow(
            workflow_id=workflow_id,
            name=self._generate_workflow_name(description),
            description=description,
            workflow_type=workflow_type,
            steps=steps,
            agents=agents,
            parameters=parameters or {}
        )

        # Apply golden ratio optimization
        self._apply_golden_optimization(workflow)

        self._workflows[workflow_id] = workflow
        self._stats["workflows_created"] += 1

        logger.info(f"Created workflow: {workflow.name} with {len(steps)} steps")
        return workflow

    async def execute_workflow(
        self,
        workflow_id: str,
        inputs: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> WorkflowExecutionResult:
        """Execute a workflow."""
        if workflow_id not in self._workflows:
            return WorkflowExecutionResult(
                workflow_id=workflow_id,
                success=False
            )

        workflow = self._workflows[workflow_id]
        start_time = time.time()

        step_results = {}
        outputs = {}
        failed_steps = 0

        # Execute steps based on workflow type
        if workflow.workflow_type == WorkflowType.LINEAR:
            for step in workflow.steps:
                result = await self._execute_step(step, inputs, context, step_results)
                step_results[step.step_id] = result
                if not result.get("success", False):
                    failed_steps += 1
                outputs.update(result.get("outputs", {}))

        elif workflow.workflow_type == WorkflowType.PARALLEL:
            # Execute all steps in parallel
            tasks = [
                self._execute_step(step, inputs, context, step_results)
                for step in workflow.steps
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for step, result in zip(workflow.steps, results):
                if isinstance(result, Exception):
                    step_results[step.step_id] = {"success": False, "error": str(result)}
                    failed_steps += 1
                else:
                    step_results[step.step_id] = result
                    outputs.update(result.get("outputs", {}))

        else:
            # Adaptive/Emergent execution
            for step in workflow.steps:
                # Check dependencies
                deps_met = all(
                    step_results.get(dep, {}).get("success", False)
                    for dep in step.depends_on
                )

                if not step.depends_on or deps_met:
                    result = await self._execute_step(step, inputs, context, step_results)
                    step_results[step.step_id] = result
                    if not result.get("success", False):
                        failed_steps += 1
                    outputs.update(result.get("outputs", {}))

        duration = (time.time() - start_time) * 1000
        success = failed_steps == 0

        # Update workflow metrics
        workflow.executions += 1
        if success:
            workflow.successes += 1
        alpha = 0.1
        workflow.avg_duration_ms = alpha * duration + (1 - alpha) * workflow.avg_duration_ms

        self._stats["workflows_executed"] += 1

        # Check for evolution trigger
        if self.auto_evolution and workflow.executions % 10 == 0:
            asyncio.create_task(self._consider_evolution(workflow))

        # Detect optimization opportunities
        bottlenecks = self._detect_bottlenecks(step_results)
        opportunities = self._find_optimization_opportunities(workflow, step_results)

        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            success=success,
            outputs=outputs,
            step_results=step_results,
            duration_ms=duration,
            steps_executed=len(step_results),
            steps_failed=failed_steps,
            bottlenecks=bottlenecks,
            optimization_opportunities=opportunities
        )

    async def evolve_workflow(
        self,
        workflow_id: str,
        strategy: str = "optimize"
    ) -> Workflow:
        """Evolve a workflow."""
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        original = self._workflows[workflow_id]
        evolved = copy.deepcopy(original)

        evolved.workflow_id = f"{workflow_id}_v{len(original.evolution_history) + 2}"
        evolved.parent_workflows = [workflow_id]

        if strategy == "optimize":
            evolved = await self._optimize_workflow(evolved)
        elif strategy == "parallelize":
            evolved = await self._parallelize_workflow(evolved)
        elif strategy == "simplify":
            evolved = await self._simplify_workflow(evolved)
        elif strategy == "expand":
            evolved = await self._expand_workflow(evolved)
        elif strategy == "transcend":
            evolved = await self._transcend_workflow(evolved)

        # Update version
        major, minor, patch = map(int, original.version.split('.'))
        if strategy == "transcend":
            evolved.version = f"{major + 1}.0.0"
        else:
            evolved.version = f"{major}.{minor + 1}.0"

        evolved.evolution_history.append({
            "from": workflow_id,
            "strategy": strategy,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Reset metrics
        evolved.executions = 0
        evolved.successes = 0
        evolved.avg_duration_ms = 0.0

        self._workflows[evolved.workflow_id] = evolved
        self._stats["workflows_evolved"] += 1

        logger.info(f"Evolved workflow {original.name} via {strategy}")
        return evolved

    async def analyze_github_workflow(
        self,
        repo_url: str
    ) -> Dict[str, Any]:
        """Analyze GitHub repository for workflow patterns."""
        # Would parse actual GitHub Actions/workflows
        analysis = {
            "repo": repo_url,
            "detected_workflows": [],
            "suggested_improvements": [],
            "competitive_advantages": []
        }

        # Simulated analysis
        analysis["detected_workflows"].append({
            "name": "CI/CD Pipeline",
            "steps": ["build", "test", "deploy"],
            "type": "linear"
        })

        analysis["suggested_improvements"].append(
            "Add parallel test execution for 2x speedup"
        )
        analysis["suggested_improvements"].append(
            "Implement caching for dependencies"
        )

        analysis["competitive_advantages"].append(
            "Add self-healing capabilities"
        )
        analysis["competitive_advantages"].append(
            "Implement predictive scaling"
        )

        return analysis

    async def create_meta_workflow(
        self,
        child_workflows: List[str],
        orchestration_type: str = "adaptive"
    ) -> Workflow:
        """Create a meta-workflow that orchestrates other workflows."""
        meta_id = f"meta_workflow_{hashlib.md5('_'.join(child_workflows).encode()).hexdigest()[:8]}"

        # Create steps that invoke child workflows
        steps = []
        for i, wf_id in enumerate(child_workflows):
            step = WorkflowStep(
                step_id=f"invoke_{wf_id}",
                name=f"Execute {wf_id}",
                description=f"Invoke child workflow: {wf_id}",
                action="invoke_workflow",
                parameters={"workflow_id": wf_id},
                golden_weight=FIBONACCI[min(i, len(FIBONACCI)-1)] / FIBONACCI[5]
            )
            steps.append(step)

        # Add orchestration steps
        steps.append(WorkflowStep(
            step_id="synthesize_results",
            name="Synthesize Results",
            description="Combine outputs from all child workflows",
            action="synthesize",
            depends_on=[s.step_id for s in steps]
        ))

        meta_workflow = Workflow(
            workflow_id=meta_id,
            name=f"Meta-Orchestrator ({len(child_workflows)} workflows)",
            description=f"Meta-workflow orchestrating: {', '.join(child_workflows)}",
            workflow_type=WorkflowType.EMERGENT,
            steps=steps,
            tags=["meta", "orchestrator"]
        )

        self._workflows[meta_id] = meta_workflow
        return meta_workflow

    async def _infer_steps(
        self,
        description: str,
        workflow_type: WorkflowType
    ) -> List[WorkflowStep]:
        """Infer workflow steps from description."""
        steps = []

        # Match against templates
        desc_lower = description.lower()
        template_match = None

        if "research" in desc_lower or "analyze" in desc_lower:
            template_match = self._workflow_templates.get("research")
        elif "develop" in desc_lower or "code" in desc_lower or "build" in desc_lower:
            template_match = self._workflow_templates.get("development")
        elif "automate" in desc_lower or "workflow" in desc_lower:
            template_match = self._workflow_templates.get("automation")
        else:
            template_match = self._workflow_templates.get("analysis")

        if template_match:
            for i, step_spec in enumerate(template_match["steps"]):
                step = WorkflowStep(
                    step_id=f"step_{i}",
                    name=step_spec["action"].replace("_", " ").title(),
                    description=f"Execute: {step_spec['action']}",
                    action=step_spec["action"],
                    depends_on=step_spec.get("depends_on", []),
                    outputs=step_spec.get("outputs", []),
                    golden_weight=FIBONACCI[min(i, len(FIBONACCI)-1)] / FIBONACCI[5]
                )
                steps.append(step)

        # If no template match, generate generic steps
        if not steps:
            steps = [
                WorkflowStep(
                    step_id="step_0",
                    name="Initialize",
                    description="Initialize workflow",
                    action="initialize"
                ),
                WorkflowStep(
                    step_id="step_1",
                    name="Process",
                    description="Main processing",
                    action="process",
                    depends_on=["step_0"]
                ),
                WorkflowStep(
                    step_id="step_2",
                    name="Finalize",
                    description="Finalize and output",
                    action="finalize",
                    depends_on=["step_1"]
                )
            ]

        return steps

    async def _compose_agent_team(
        self,
        steps: List[WorkflowStep]
    ) -> List[MicroAgent]:
        """Compose optimal agent team for workflow steps."""
        agents = []

        # Always have a coordinator
        coordinator = MicroAgent(
            agent_id=f"agent_coord_{len(self._agents)}",
            name="Coordinator",
            role=AgentRole.COORDINATOR,
            skills=["orchestration", "planning", "monitoring"]
        )
        agents.append(coordinator)
        self._agents[coordinator.agent_id] = coordinator

        # Create specialized agents based on steps
        for step in steps:
            action = step.action.lower()

            if "analyze" in action or "validate" in action:
                agent = MicroAgent(
                    agent_id=f"agent_analyzer_{len(self._agents)}",
                    name="Analyzer",
                    role=AgentRole.ANALYZER,
                    skills=["analysis", "validation", "pattern_recognition"],
                    precision=0.9
                )
            elif "generate" in action or "create" in action:
                agent = MicroAgent(
                    agent_id=f"agent_executor_{len(self._agents)}",
                    name="Creator",
                    role=AgentRole.EXECUTOR,
                    skills=["generation", "creation", "execution"],
                    creativity=0.9
                )
            elif "optimize" in action:
                agent = MicroAgent(
                    agent_id=f"agent_optimizer_{len(self._agents)}",
                    name="Optimizer",
                    role=AgentRole.OPTIMIZER,
                    skills=["optimization", "improvement", "efficiency"]
                )
            else:
                agent = MicroAgent(
                    agent_id=f"agent_exec_{len(self._agents)}",
                    name="Executor",
                    role=AgentRole.EXECUTOR,
                    skills=["execution", "processing"]
                )

            if agent.agent_id not in self._agents:
                agents.append(agent)
                self._agents[agent.agent_id] = agent

        self._stats["agents_spawned"] += len(agents)
        return agents

    def _apply_golden_optimization(self, workflow: Workflow):
        """Apply golden ratio optimization to workflow."""
        # Optimize step weights using golden ratio
        for i, step in enumerate(workflow.steps):
            step.golden_weight = 1 / (PHI ** i)

        # Normalize
        total_weight = sum(s.golden_weight for s in workflow.steps)
        for step in workflow.steps:
            step.golden_weight /= total_weight

    async def _execute_step(
        self,
        step: WorkflowStep,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        start_time = time.time()

        try:
            # Simulate step execution
            if self.llm_provider:
                prompt = f"Execute step: {step.name}\nDescription: {step.description}\nInputs: {inputs}"
                result = await self.llm_provider(prompt)
                output = {"result": result}
            else:
                output = {"result": f"Executed: {step.action}"}

            duration = (time.time() - start_time) * 1000

            # Update step metrics
            alpha = 0.1
            step.avg_execution_time_ms = alpha * duration + (1 - alpha) * step.avg_execution_time_ms

            return {
                "success": True,
                "outputs": output,
                "duration_ms": duration
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }

    async def _consider_evolution(self, workflow: Workflow):
        """Consider evolving a workflow based on performance."""
        if workflow.success_rate < 0.7:
            await self.evolve_workflow(workflow.workflow_id, "simplify")
        elif workflow.avg_duration_ms > 10000:
            await self.evolve_workflow(workflow.workflow_id, "optimize")
        elif workflow.success_rate > 0.95:
            await self.evolve_workflow(workflow.workflow_id, "expand")

    async def _optimize_workflow(self, workflow: Workflow) -> Workflow:
        """Optimize workflow for performance."""
        # Reorder steps by golden weight
        workflow.steps.sort(key=lambda s: s.golden_weight, reverse=True)

        # Increase parallelization
        for step in workflow.steps:
            step.can_parallelize = True

        workflow.description = f"[Optimized] {workflow.description}"
        return workflow

    async def _parallelize_workflow(self, workflow: Workflow) -> Workflow:
        """Convert to parallel workflow."""
        workflow.workflow_type = WorkflowType.PARALLEL

        # Remove unnecessary dependencies
        for step in workflow.steps:
            step.depends_on = []
            step.can_parallelize = True

        workflow.description = f"[Parallelized] {workflow.description}"
        return workflow

    async def _simplify_workflow(self, workflow: Workflow) -> Workflow:
        """Simplify workflow by removing low-value steps."""
        # Keep only high-weight steps
        workflow.steps = [s for s in workflow.steps if s.golden_weight > 0.1]

        # Ensure at least some steps remain
        if not workflow.steps:
            workflow.steps = [WorkflowStep(
                step_id="simplified",
                name="Simplified",
                description="Simplified execution",
                action="execute"
            )]

        workflow.description = f"[Simplified] {workflow.description}"
        return workflow

    async def _expand_workflow(self, workflow: Workflow) -> Workflow:
        """Expand workflow with additional capabilities."""
        # Add optimization step
        workflow.steps.append(WorkflowStep(
            step_id=f"expand_optimize_{len(workflow.steps)}",
            name="Self-Optimize",
            description="Analyze and optimize execution",
            action="self_optimize"
        ))

        # Add validation step
        workflow.steps.append(WorkflowStep(
            step_id=f"expand_validate_{len(workflow.steps)}",
            name="Validate Results",
            description="Validate all outputs",
            action="validate"
        ))

        workflow.description = f"[Expanded] {workflow.description}"
        return workflow

    async def _transcend_workflow(self, workflow: Workflow) -> Workflow:
        """Transcend workflow to meta-level."""
        workflow.workflow_type = WorkflowType.TRANSCENDENT

        # Add meta-capabilities
        workflow.steps.append(WorkflowStep(
            step_id="transcend_evolve",
            name="Self-Evolve",
            description="Automatically evolve based on performance",
            action="self_evolve"
        ))

        workflow.steps.append(WorkflowStep(
            step_id="transcend_learn",
            name="Learn Patterns",
            description="Extract and apply learned patterns",
            action="pattern_learning"
        ))

        workflow.tags.append("transcendent")
        workflow.description = f"[Transcendent] {workflow.description}"
        return workflow

    def _detect_bottlenecks(
        self,
        step_results: Dict[str, Any]
    ) -> List[str]:
        """Detect bottlenecks in execution."""
        bottlenecks = []

        for step_id, result in step_results.items():
            duration = result.get("duration_ms", 0)
            if duration > 1000:  # > 1 second
                bottlenecks.append(f"{step_id}: {duration:.0f}ms")

        return bottlenecks

    def _find_optimization_opportunities(
        self,
        workflow: Workflow,
        step_results: Dict[str, Any]
    ) -> List[str]:
        """Find optimization opportunities."""
        opportunities = []

        # Check for parallelization opportunities
        independent_steps = [
            s for s in workflow.steps
            if not s.depends_on
        ]
        if len(independent_steps) > 1:
            opportunities.append(
                f"Parallelize {len(independent_steps)} independent steps"
            )

        # Check for caching opportunities
        slow_steps = [
            s for s in workflow.steps
            if s.avg_execution_time_ms > 500
        ]
        if slow_steps:
            opportunities.append(
                f"Cache results for {len(slow_steps)} slow steps"
            )

        return opportunities

    def _generate_workflow_name(self, description: str) -> str:
        """Generate workflow name from description."""
        words = description.split()[:4]
        return " ".join(w.title() for w in words if len(w) > 2)

    def get_stats(self) -> Dict[str, Any]:
        """Get genesis statistics."""
        return {
            **self._stats,
            "total_workflows": len(self._workflows),
            "total_agents": len(self._agents)
        }


# Global instance
_workflow_genesis: Optional[AutomatedWorkflowGenesis] = None


def get_workflow_genesis() -> AutomatedWorkflowGenesis:
    """Get the global workflow genesis."""
    global _workflow_genesis
    if _workflow_genesis is None:
        _workflow_genesis = AutomatedWorkflowGenesis()
    return _workflow_genesis


async def demo():
    """Demonstrate Automated Workflow Genesis."""
    genesis = get_workflow_genesis()

    print("=== AUTOMATED WORKFLOW GENESIS DEMO ===\n")

    # Create a workflow
    print("--- Creating Workflow ---")
    workflow = await genesis.create_workflow(
        description="Research and analyze AI competitors, then generate improvement recommendations",
        workflow_type=WorkflowType.ADAPTIVE
    )
    print(f"Created: {workflow.name}")
    print(f"  Type: {workflow.workflow_type.name}")
    print(f"  Steps: {len(workflow.steps)}")
    print(f"  Agents: {len(workflow.agents)}")

    # Execute workflow
    print("\n--- Executing Workflow ---")
    result = await genesis.execute_workflow(
        workflow.workflow_id,
        inputs={"topic": "AI agents"},
        context={}
    )
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_ms:.2f}ms")
    print(f"Steps executed: {result.steps_executed}")

    if result.bottlenecks:
        print(f"Bottlenecks: {result.bottlenecks}")
    if result.optimization_opportunities:
        print(f"Opportunities: {result.optimization_opportunities}")

    # Evolve workflow
    print("\n--- Evolving Workflow ---")
    evolved = await genesis.evolve_workflow(
        workflow.workflow_id,
        strategy="optimize"
    )
    print(f"Evolved to: {evolved.version}")

    # Show stats
    print("\n--- Statistics ---")
    for key, value in genesis.get_stats().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
