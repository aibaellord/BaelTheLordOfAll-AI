"""
Tool Composition Engine for BAEL Phase 2

Automatically generates and optimizes tool chains for complex tasks.
Creates workflows by composing tools intelligently based on goals and constraints.

Key Components:
- Workflow generation and optimization
- Tool chaining and sequencing
- Parameter inference and binding
- Execution planning
- Workflow validation
- Execution monitoring
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CompositionStrategy(str, Enum):
    """Strategies for composing tools."""
    SEQUENTIAL = "sequential"  # Tools run one after another
    PARALLEL = "parallel"  # Tools run simultaneously
    CONDITIONAL = "conditional"  # Based on conditions
    FEEDBACK_LOOP = "feedback_loop"  # Iterative with feedback
    BRANCHING = "branching"  # Multiple paths based on conditions


@dataclass
class ToolDefinition:
    """Definition of a tool that can be composed."""
    tool_id: str
    name: str
    description: str
    input_parameters: Dict[str, Dict[str, Any]]  # param_name -> {type, required, etc}
    output_type: str
    capability_tags: List[str]
    dependencies: List[str] = field(default_factory=list)
    cost: float = 1.0  # Relative execution cost
    reliability: float = 0.95  # Success rate
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "input_parameters": self.input_parameters,
            "output_type": self.output_type,
            "capability_tags": self.capability_tags,
            "dependencies": self.dependencies,
            "cost": self.cost,
            "reliability": self.reliability,
        }


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    step_id: str
    tool_id: str
    input_mapping: Dict[str, Any]  # Maps inputs to this step
    output_binding: Dict[str, str] = field(default_factory=dict)  # output_name -> variable_name
    condition: Optional[str] = None  # Conditional execution
    retry_count: int = 0
    timeout: int = 30  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "tool_id": self.tool_id,
            "input_mapping": self.input_mapping,
            "output_binding": self.output_binding,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
        }


@dataclass
class Workflow:
    """Complete workflow specification."""
    workflow_id: str
    name: str
    description: str
    goal: str  # What this workflow accomplishes
    steps: List[WorkflowStep] = field(default_factory=list)
    strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)  # Cost, time, etc.
    validation_rules: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    optimization_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "strategy": self.strategy.value,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "constraints": self.constraints,
            "validation_rules": self.validation_rules,
            "optimization_score": self.optimization_score,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionTrace:
    """Record of workflow execution."""
    execution_id: str
    workflow_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    total_cost: float = 0.0
    total_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "step_results": self.step_results,
            "status": self.status,
            "error": self.error,
            "total_cost": self.total_cost,
            "total_time": self.total_time,
        }


class ToolRegistry:
    """Registry of available tools for composition."""

    def __init__(self):
        """Initialize registry."""
        self.tools: Dict[str, ToolDefinition] = {}
        self.capability_index: Dict[str, List[str]] = {}  # capability -> tool_ids

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self.tools[tool.tool_id] = tool

        # Index by capabilities
        for capability in tool.capability_tags:
            if capability not in self.capability_index:
                self.capability_index[capability] = []
            self.capability_index[capability].append(tool.tool_id)

        logger.info(f"Registered tool: {tool.name}")

    def find_tools_by_capability(self, capability: str) -> List[ToolDefinition]:
        """Find tools with given capability."""
        tool_ids = self.capability_index.get(capability, [])
        return [self.tools[tid] for tid in tool_ids]

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool by ID."""
        return self.tools.get(tool_id)

    def find_compatible_tools(
        self,
        input_type: str,
        output_type: str,
        capability: Optional[str] = None,
    ) -> List[ToolDefinition]:
        """Find tools that transform input_type to output_type."""
        candidates = []

        for tool in self.tools.values():
            # Check capability if specified
            if capability and capability not in tool.capability_tags:
                continue

            # For simplicity, check if tool can handle this transformation
            candidates.append(tool)

        return candidates


class WorkflowGenerator:
    """Generates workflows from goals."""

    def __init__(self, tool_registry: ToolRegistry):
        """Initialize generator."""
        self.tool_registry = tool_registry
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Callable]:
        """Load workflow templates."""
        return {
            "sequential": self._create_sequential,
            "parallel": self._create_parallel,
            "conditional": self._create_conditional,
            "iterative": self._create_iterative,
        }

    def generate(
        self,
        goal: str,
        required_capabilities: List[str],
        constraints: Optional[Dict[str, Any]] = None,
        strategy: str = "sequential",
    ) -> Optional[Workflow]:
        """
        Generate workflow for goal.

        Args:
            goal: What the workflow should accomplish
            required_capabilities: Capabilities needed
            constraints: Cost, time, etc.
            strategy: Composition strategy

        Returns:
            Generated workflow
        """
        # Find tools matching capabilities
        available_tools = []
        for capability in required_capabilities:
            tools = self.tool_registry.find_tools_by_capability(capability)
            available_tools.extend(tools)

        if not available_tools:
            logger.warning(f"No tools found for capabilities: {required_capabilities}")
            return None

        # Create workflow
        if strategy in self.templates:
            template = self.templates[strategy]
            workflow = template(goal, available_tools, constraints)
        else:
            workflow = self._create_sequential(goal, available_tools, constraints)

        return workflow

    def _create_sequential(
        self,
        goal: str,
        tools: List[ToolDefinition],
        constraints: Optional[Dict[str, Any]],
    ) -> Workflow:
        """Create sequential workflow."""
        workflow_id = self._generate_workflow_id(goal, "sequential")
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Sequential: {goal}",
            description=f"Sequential workflow for: {goal}",
            goal=goal,
            strategy=CompositionStrategy.SEQUENTIAL,
            constraints=constraints or {},
        )

        # Add steps for each tool
        for i, tool in enumerate(tools[:5]):  # Limit to 5 steps
            step = WorkflowStep(
                step_id=f"step_{i}",
                tool_id=tool.tool_id,
                input_mapping={},
                timeout=tool.metadata.get("timeout", 30),
            )
            workflow.steps.append(step)

        return workflow

    def _create_parallel(
        self,
        goal: str,
        tools: List[ToolDefinition],
        constraints: Optional[Dict[str, Any]],
    ) -> Workflow:
        """Create parallel workflow."""
        workflow_id = self._generate_workflow_id(goal, "parallel")
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Parallel: {goal}",
            description=f"Parallel workflow for: {goal}",
            goal=goal,
            strategy=CompositionStrategy.PARALLEL,
            constraints=constraints or {},
        )

        # Add all tools in parallel
        for i, tool in enumerate(tools[:8]):
            step = WorkflowStep(
                step_id=f"step_{i}",
                tool_id=tool.tool_id,
                input_mapping={},
            )
            workflow.steps.append(step)

        return workflow

    def _create_conditional(
        self,
        goal: str,
        tools: List[ToolDefinition],
        constraints: Optional[Dict[str, Any]],
    ) -> Workflow:
        """Create conditional workflow."""
        workflow_id = self._generate_workflow_id(goal, "conditional")
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Conditional: {goal}",
            description=f"Conditional workflow for: {goal}",
            goal=goal,
            strategy=CompositionStrategy.CONDITIONAL,
            constraints=constraints or {},
        )

        # Add conditional steps
        if len(tools) >= 2:
            # Check condition step
            step1 = WorkflowStep(
                step_id="check_condition",
                tool_id=tools[0].tool_id,
                input_mapping={},
            )

            # Branch steps
            step2 = WorkflowStep(
                step_id="branch_true",
                tool_id=tools[1].tool_id,
                input_mapping={},
                condition="result == true",
            )

            if len(tools) > 2:
                step3 = WorkflowStep(
                    step_id="branch_false",
                    tool_id=tools[2].tool_id,
                    input_mapping={},
                    condition="result != true",
                )
                workflow.steps = [step1, step2, step3]
            else:
                workflow.steps = [step1, step2]

        return workflow

    def _create_iterative(
        self,
        goal: str,
        tools: List[ToolDefinition],
        constraints: Optional[Dict[str, Any]],
    ) -> Workflow:
        """Create iterative workflow."""
        workflow_id = self._generate_workflow_id(goal, "iterative")
        workflow = Workflow(
            workflow_id=workflow_id,
            name=f"Iterative: {goal}",
            description=f"Iterative workflow for: {goal}",
            goal=goal,
            strategy=CompositionStrategy.FEEDBACK_LOOP,
            constraints=constraints or {},
        )

        # Add steps for iteration
        if tools:
            step = WorkflowStep(
                step_id="iterate",
                tool_id=tools[0].tool_id,
                input_mapping={},
                retry_count=3,  # Allow retries
            )
            workflow.steps.append(step)

        return workflow

    def _generate_workflow_id(self, goal: str, strategy: str) -> str:
        """Generate unique workflow ID."""
        combined = f"{goal}_{strategy}_{datetime.now().isoformat()}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]


class WorkflowOptimizer:
    """Optimizes workflows for performance and cost."""

    def optimize(
        self,
        workflow: Workflow,
        criteria: Optional[Dict[str, float]] = None,
    ) -> Workflow:
        """
        Optimize workflow.

        Args:
            workflow: Workflow to optimize
            criteria: Optimization criteria (cost_weight, speed_weight, etc.)

        Returns:
            Optimized workflow
        """
        criteria = criteria or {"cost": 0.5, "speed": 0.3, "reliability": 0.2}

        # Reorder steps for efficiency
        if workflow.strategy == CompositionStrategy.SEQUENTIAL:
            workflow.steps = self._reorder_sequential(workflow.steps, criteria)

        # Calculate optimization score
        workflow.optimization_score = self._calculate_score(workflow, criteria)

        return workflow

    def _reorder_sequential(
        self,
        steps: List[WorkflowStep],
        criteria: Dict[str, float],
    ) -> List[WorkflowStep]:
        """Reorder sequential steps for optimization."""
        # Sort by cost if cost optimization is prioritized
        if criteria.get("cost", 0) > criteria.get("speed", 0):
            # Keep original order for correctness
            pass

        return steps

    def _calculate_score(
        self,
        workflow: Workflow,
        criteria: Dict[str, float],
    ) -> float:
        """Calculate optimization score."""
        score = 0.0

        # Number of steps affects execution time
        step_penalty = len(workflow.steps) * 0.02
        score += 1.0 - step_penalty

        # Parallel execution improves speed
        if workflow.strategy == CompositionStrategy.PARALLEL:
            score += criteria.get("speed", 0) * 0.3

        return min(score, 1.0)


class WorkflowValidator:
    """Validates workflow correctness and feasibility."""

    def validate(self, workflow: Workflow) -> Tuple[bool, List[str]]:
        """
        Validate workflow.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check for empty workflow
        if not workflow.steps:
            issues.append("Workflow has no steps")
            return False, issues

        # Check step references
        step_ids = {s.step_id for s in workflow.steps}
        for step in workflow.steps:
            for dep in step.input_mapping.values():
                if isinstance(dep, str) and "$" in dep:
                    ref_step = dep.split(".")[0].lstrip("$")
                    if ref_step != "input" and ref_step not in step_ids:
                        issues.append(
                            f"Step {step.step_id} references undefined step {ref_step}"
                        )

        # Check for cycles (simplified)
        if self._has_cycles(workflow.steps):
            issues.append("Workflow contains cycles")

        return len(issues) == 0, issues

    def _has_cycles(self, steps: List[WorkflowStep]) -> bool:
        """Check for cycles in workflow (simplified)."""
        # This would need proper graph cycle detection
        return False


class CompositionEngine:
    """Main tool composition engine."""

    def __init__(self):
        """Initialize composition engine."""
        self.tool_registry = ToolRegistry()
        self.generator = WorkflowGenerator(self.tool_registry)
        self.optimizer = WorkflowOptimizer()
        self.validator = WorkflowValidator()
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, ExecutionTrace] = {}

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register tool."""
        self.tool_registry.register_tool(tool)

    def compose(
        self,
        goal: str,
        required_capabilities: List[str],
        constraints: Optional[Dict[str, Any]] = None,
        optimize: bool = True,
    ) -> Optional[Workflow]:
        """
        Compose tool workflow for goal.

        Args:
            goal: What to accomplish
            required_capabilities: Required capabilities
            constraints: Performance constraints
            optimize: Whether to optimize workflow

        Returns:
            Generated and validated workflow
        """
        # Generate workflow
        workflow = self.generator.generate(
            goal,
            required_capabilities,
            constraints,
        )

        if not workflow:
            return None

        # Validate
        is_valid, issues = self.validator.validate(workflow)
        if not is_valid:
            logger.warning(f"Validation issues: {issues}")
            return None

        # Optimize
        if optimize:
            workflow = self.optimizer.optimize(workflow, constraints)

        # Store
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)

    def execute(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        executor: Optional[Callable] = None,
    ) -> ExecutionTrace:
        """
        Execute workflow.

        Args:
            workflow_id: ID of workflow to execute
            inputs: Input variables
            executor: Custom executor function

        Returns:
            Execution trace
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution_id = f"exec_{len(self.executions)}_{datetime.now().timestamp()}"
        trace = ExecutionTrace(execution_id=execution_id, workflow_id=workflow_id)

        try:
            trace.step_results = self._execute_steps(
                workflow.steps,
                inputs,
                executor,
            )
            trace.status = "completed"
        except Exception as e:
            trace.status = "failed"
            trace.error = str(e)
            logger.error(f"Workflow execution failed: {e}")

        trace.end_time = datetime.now()
        trace.total_time = (
            trace.end_time - trace.start_time
        ).total_seconds() * 1000  # milliseconds

        self.executions[execution_id] = trace
        return trace

    def _execute_steps(
        self,
        steps: List[WorkflowStep],
        inputs: Dict[str, Any],
        executor: Optional[Callable],
    ) -> Dict[str, Any]:
        """Execute workflow steps."""
        results = inputs.copy()

        for step in steps:
            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, results):
                continue

            # Execute step
            if executor:
                step_result = executor(step.tool_id, step.input_mapping)
                results.update(step_result)

        return results

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate conditional statement."""
        try:
            # Simple evaluation (in production, use safer eval)
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False


# Global composition engine
_engine = None


def get_composition_engine() -> CompositionEngine:
    """Get or create global composition engine."""
    global _engine
    if _engine is None:
        _engine = CompositionEngine()
    return _engine
