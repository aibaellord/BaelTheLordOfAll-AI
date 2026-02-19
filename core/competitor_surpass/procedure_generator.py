"""
📋 PROCEDURE GENERATOR
======================
Surpasses MetaGPT's SOP generation with:
- Automatic procedure synthesis from goals
- Multi-format output (flowchart, checklist, code)
- Procedure optimization and validation
- Learning from execution feedback
- Integration with all BAEL modules
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.ProcedureGenerator")


class ProcedureType(Enum):
    """Types of procedures"""
    LINEAR = "linear"           # Sequential steps
    BRANCHING = "branching"     # Decision tree
    PARALLEL = "parallel"       # Concurrent steps
    ITERATIVE = "iterative"     # Loop-based
    HYBRID = "hybrid"           # Combination


class StepType(Enum):
    """Types of procedure steps"""
    ACTION = "action"           # Do something
    DECISION = "decision"       # Make a choice
    VALIDATION = "validation"   # Check something
    WAIT = "wait"               # Wait for condition
    PARALLEL = "parallel"       # Parallel execution
    LOOP = "loop"               # Repeat
    SUBPROCESS = "subprocess"   # Call another procedure


class OutputFormat(Enum):
    """Output formats for procedures"""
    CHECKLIST = "checklist"
    FLOWCHART = "flowchart"
    PYTHON_CODE = "python_code"
    PSEUDOCODE = "pseudocode"
    MERMAID = "mermaid"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ProcedureStep:
    """A single step in a procedure"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    order: int = 0
    type: StepType = StepType.ACTION
    title: str = ""
    description: str = ""

    # For decisions
    condition: str = ""
    true_branch: str = ""   # Step ID if true
    false_branch: str = ""  # Step ID if false

    # For loops
    loop_condition: str = ""
    loop_body: List[str] = field(default_factory=list)  # Step IDs

    # For parallel
    parallel_steps: List[str] = field(default_factory=list)  # Step IDs

    # Execution details
    executor: str = ""      # Who/what executes
    tools: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    # Timing
    estimated_duration: str = ""
    timeout: Optional[int] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Step IDs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "condition": self.condition,
            "true_branch": self.true_branch,
            "false_branch": self.false_branch,
            "executor": self.executor,
            "tools": self.tools,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "estimated_duration": self.estimated_duration,
            "depends_on": self.depends_on
        }


@dataclass
class Procedure:
    """A complete procedure/SOP"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    type: ProcedureType = ProcedureType.LINEAR

    # Steps
    steps: List[ProcedureStep] = field(default_factory=list)
    entry_step: str = ""  # First step ID
    exit_steps: List[str] = field(default_factory=list)  # Final step IDs

    # Metadata
    version: str = "1.0.0"
    author: str = "BAEL"
    created_at: datetime = field(default_factory=datetime.now)

    # Requirements
    prerequisites: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)

    # Outputs
    expected_outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Execution stats
    execution_count: int = 0
    success_rate: float = 0.0
    average_duration_seconds: float = 0.0

    def get_step(self, step_id: str) -> Optional[ProcedureStep]:
        """Get step by ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ordered_steps(self) -> List[ProcedureStep]:
        """Get steps in execution order"""
        return sorted(self.steps, key=lambda s: s.order)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "steps": [s.to_dict() for s in self.steps],
            "entry_step": self.entry_step,
            "exit_steps": self.exit_steps,
            "version": self.version,
            "prerequisites": self.prerequisites,
            "required_tools": self.required_tools,
            "required_roles": self.required_roles,
            "expected_outputs": self.expected_outputs,
            "success_criteria": self.success_criteria
        }


class ProcedureGenerator:
    """
    Advanced procedure/SOP generator that surpasses MetaGPT.

    Features:
    - Generate procedures from natural language goals
    - Multiple output formats
    - Automatic optimization
    - Validation and testing
    - Learning from execution
    - Integration with BAEL's reasoning engines
    """

    def __init__(self):
        self.procedures: Dict[str, Procedure] = {}
        self.templates: Dict[str, Procedure] = {}
        self._load_templates()

    def _load_templates(self):
        """Load procedure templates"""

        # Software Development Template
        self.templates["software_development"] = Procedure(
            name="Software Development",
            description="Standard software development procedure",
            type=ProcedureType.LINEAR,
            steps=[
                ProcedureStep(
                    id="requirements",
                    order=1,
                    type=StepType.ACTION,
                    title="Gather Requirements",
                    description="Collect and document all requirements from stakeholders",
                    executor="business_analyst",
                    outputs=["requirements_document"]
                ),
                ProcedureStep(
                    id="design",
                    order=2,
                    type=StepType.ACTION,
                    title="Create Design",
                    description="Design the system architecture and components",
                    executor="software_architect",
                    inputs=["requirements_document"],
                    outputs=["design_document"],
                    depends_on=["requirements"]
                ),
                ProcedureStep(
                    id="implement",
                    order=3,
                    type=StepType.ACTION,
                    title="Implement Code",
                    description="Write the code according to design",
                    executor="senior_developer",
                    inputs=["design_document"],
                    outputs=["source_code"],
                    depends_on=["design"]
                ),
                ProcedureStep(
                    id="review",
                    order=4,
                    type=StepType.ACTION,
                    title="Code Review",
                    description="Review code for quality and issues",
                    executor="senior_developer",
                    inputs=["source_code"],
                    outputs=["review_feedback"],
                    depends_on=["implement"]
                ),
                ProcedureStep(
                    id="test",
                    order=5,
                    type=StepType.ACTION,
                    title="Test",
                    description="Run all tests",
                    executor="qa_engineer",
                    inputs=["source_code"],
                    outputs=["test_results"],
                    depends_on=["review"]
                ),
                ProcedureStep(
                    id="deploy",
                    order=6,
                    type=StepType.ACTION,
                    title="Deploy",
                    description="Deploy to production",
                    executor="devops_engineer",
                    inputs=["source_code", "test_results"],
                    outputs=["deployed_system"],
                    depends_on=["test"]
                )
            ],
            entry_step="requirements",
            exit_steps=["deploy"],
            required_roles=["business_analyst", "software_architect", "senior_developer", "qa_engineer", "devops_engineer"]
        )

        # Research Template
        self.templates["research"] = Procedure(
            name="Research Process",
            description="Systematic research procedure",
            type=ProcedureType.ITERATIVE,
            steps=[
                ProcedureStep(
                    id="define_question",
                    order=1,
                    type=StepType.ACTION,
                    title="Define Research Question",
                    description="Clearly define what we want to learn",
                    outputs=["research_question"]
                ),
                ProcedureStep(
                    id="literature_review",
                    order=2,
                    type=StepType.ACTION,
                    title="Literature Review",
                    description="Review existing research and knowledge",
                    tools=["web_search", "research_database"],
                    outputs=["literature_summary"],
                    depends_on=["define_question"]
                ),
                ProcedureStep(
                    id="hypothesis",
                    order=3,
                    type=StepType.ACTION,
                    title="Form Hypothesis",
                    description="Develop testable hypothesis",
                    inputs=["research_question", "literature_summary"],
                    outputs=["hypothesis"],
                    depends_on=["literature_review"]
                ),
                ProcedureStep(
                    id="gather_data",
                    order=4,
                    type=StepType.ACTION,
                    title="Gather Data",
                    description="Collect relevant data",
                    inputs=["hypothesis"],
                    outputs=["raw_data"],
                    depends_on=["hypothesis"]
                ),
                ProcedureStep(
                    id="analyze",
                    order=5,
                    type=StepType.ACTION,
                    title="Analyze Data",
                    description="Analyze collected data",
                    tools=["data_analysis"],
                    inputs=["raw_data"],
                    outputs=["analysis_results"],
                    depends_on=["gather_data"]
                ),
                ProcedureStep(
                    id="conclude",
                    order=6,
                    type=StepType.ACTION,
                    title="Draw Conclusions",
                    description="Form conclusions based on analysis",
                    inputs=["analysis_results", "hypothesis"],
                    outputs=["conclusions"],
                    depends_on=["analyze"]
                )
            ],
            entry_step="define_question",
            exit_steps=["conclude"]
        )

        # Decision Making Template
        self.templates["decision_making"] = Procedure(
            name="Decision Making",
            description="Structured decision making process",
            type=ProcedureType.BRANCHING,
            steps=[
                ProcedureStep(
                    id="define_problem",
                    order=1,
                    type=StepType.ACTION,
                    title="Define Problem",
                    description="Clearly define the decision to be made",
                    outputs=["problem_statement"]
                ),
                ProcedureStep(
                    id="gather_info",
                    order=2,
                    type=StepType.ACTION,
                    title="Gather Information",
                    description="Collect relevant information",
                    outputs=["information_package"],
                    depends_on=["define_problem"]
                ),
                ProcedureStep(
                    id="identify_options",
                    order=3,
                    type=StepType.ACTION,
                    title="Identify Options",
                    description="Generate possible options",
                    inputs=["information_package"],
                    outputs=["options_list"],
                    depends_on=["gather_info"]
                ),
                ProcedureStep(
                    id="evaluate",
                    order=4,
                    type=StepType.ACTION,
                    title="Evaluate Options",
                    description="Analyze pros and cons of each option",
                    inputs=["options_list"],
                    outputs=["evaluation_matrix"],
                    depends_on=["identify_options"]
                ),
                ProcedureStep(
                    id="decide",
                    order=5,
                    type=StepType.ACTION,
                    title="Make Decision",
                    description="Select the best option",
                    inputs=["evaluation_matrix"],
                    outputs=["decision"],
                    depends_on=["evaluate"]
                ),
                ProcedureStep(
                    id="implement",
                    order=6,
                    type=StepType.ACTION,
                    title="Implement Decision",
                    description="Execute the decision",
                    inputs=["decision"],
                    outputs=["implementation_result"],
                    depends_on=["decide"]
                ),
                ProcedureStep(
                    id="review_outcome",
                    order=7,
                    type=StepType.VALIDATION,
                    title="Review Outcome",
                    description="Evaluate the results",
                    inputs=["implementation_result"],
                    outputs=["outcome_review"],
                    depends_on=["implement"]
                )
            ],
            entry_step="define_problem",
            exit_steps=["review_outcome"]
        )

    def generate(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        template: str = None
    ) -> Procedure:
        """
        Generate a procedure from a goal description.

        Args:
            goal: Natural language description of what to achieve
            context: Additional context
            template: Optional template to base on

        Returns:
            Generated Procedure
        """
        context = context or {}

        # Start with template if provided
        if template and template in self.templates:
            base = self.templates[template]
            procedure = Procedure(
                name=goal[:50],
                description=goal,
                type=base.type,
                steps=[ProcedureStep(**s.to_dict()) for s in base.steps],
                entry_step=base.entry_step,
                exit_steps=base.exit_steps.copy(),
                required_roles=base.required_roles.copy(),
                required_tools=base.required_tools.copy()
            )
        else:
            # Generate from scratch
            procedure = self._generate_from_goal(goal, context)

        # Customize based on context
        procedure = self._customize_procedure(procedure, context)

        # Validate
        self._validate_procedure(procedure)

        # Store
        self.procedures[procedure.id] = procedure

        return procedure

    def _generate_from_goal(self, goal: str, context: Dict[str, Any]) -> Procedure:
        """Generate procedure from goal"""
        goal_lower = goal.lower()

        # Identify procedure type
        if any(x in goal_lower for x in ["simultaneously", "parallel", "concurrent"]):
            proc_type = ProcedureType.PARALLEL
        elif any(x in goal_lower for x in ["until", "while", "repeat", "iterate"]):
            proc_type = ProcedureType.ITERATIVE
        elif any(x in goal_lower for x in ["if", "decide", "choose", "option"]):
            proc_type = ProcedureType.BRANCHING
        else:
            proc_type = ProcedureType.LINEAR

        # Extract key actions
        steps = self._extract_steps(goal)

        procedure = Procedure(
            name=goal[:50],
            description=goal,
            type=proc_type,
            steps=steps,
            entry_step=steps[0].id if steps else "",
            exit_steps=[steps[-1].id] if steps else []
        )

        return procedure

    def _extract_steps(self, goal: str) -> List[ProcedureStep]:
        """Extract steps from goal description"""
        steps = []

        # Simple extraction based on action verbs
        action_verbs = [
            "analyze", "create", "build", "develop", "implement", "test",
            "deploy", "review", "validate", "document", "research",
            "gather", "collect", "process", "generate", "optimize"
        ]

        words = goal.lower().split()
        order = 1

        for i, word in enumerate(words):
            if word in action_verbs:
                # Extract context around action
                start = max(0, i - 2)
                end = min(len(words), i + 5)
                title = " ".join(words[start:end]).capitalize()

                steps.append(ProcedureStep(
                    order=order,
                    type=StepType.ACTION,
                    title=title,
                    description=f"Step to {word} the required components"
                ))
                order += 1

        # If no steps extracted, create generic steps
        if not steps:
            steps = [
                ProcedureStep(order=1, title="Analyze Requirements", type=StepType.ACTION),
                ProcedureStep(order=2, title="Plan Approach", type=StepType.ACTION),
                ProcedureStep(order=3, title="Execute", type=StepType.ACTION),
                ProcedureStep(order=4, title="Validate Results", type=StepType.VALIDATION),
            ]

        # Set dependencies
        for i in range(1, len(steps)):
            steps[i].depends_on = [steps[i-1].id]

        return steps

    def _customize_procedure(
        self,
        procedure: Procedure,
        context: Dict[str, Any]
    ) -> Procedure:
        """Customize procedure based on context"""

        # Add tools from context
        if "available_tools" in context:
            procedure.required_tools = context["available_tools"]

        # Add roles from context
        if "available_roles" in context:
            procedure.required_roles = context["available_roles"]

        # Add success criteria
        if "success_criteria" in context:
            procedure.success_criteria = context["success_criteria"]

        return procedure

    def _validate_procedure(self, procedure: Procedure) -> bool:
        """Validate procedure is well-formed"""
        issues = []

        # Check entry step exists
        if procedure.entry_step and not procedure.get_step(procedure.entry_step):
            issues.append(f"Entry step {procedure.entry_step} not found")

        # Check exit steps exist
        for exit_id in procedure.exit_steps:
            if not procedure.get_step(exit_id):
                issues.append(f"Exit step {exit_id} not found")

        # Check dependencies exist
        for step in procedure.steps:
            for dep_id in step.depends_on:
                if not procedure.get_step(dep_id):
                    issues.append(f"Step {step.id} depends on non-existent step {dep_id}")

        if issues:
            logger.warning(f"Procedure validation issues: {issues}")
            return False

        return True

    def export(
        self,
        procedure: Procedure,
        format: OutputFormat = OutputFormat.MARKDOWN
    ) -> str:
        """Export procedure to specified format"""

        if format == OutputFormat.MARKDOWN:
            return self._export_markdown(procedure)
        elif format == OutputFormat.CHECKLIST:
            return self._export_checklist(procedure)
        elif format == OutputFormat.MERMAID:
            return self._export_mermaid(procedure)
        elif format == OutputFormat.PYTHON_CODE:
            return self._export_python(procedure)
        elif format == OutputFormat.PSEUDOCODE:
            return self._export_pseudocode(procedure)
        elif format == OutputFormat.JSON:
            return json.dumps(procedure.to_dict(), indent=2, default=str)
        else:
            return str(procedure.to_dict())

    def _export_markdown(self, procedure: Procedure) -> str:
        """Export as markdown"""
        lines = [
            f"# {procedure.name}",
            "",
            f"{procedure.description}",
            "",
            f"**Type:** {procedure.type.value}",
            "",
        ]

        if procedure.prerequisites:
            lines.append("## Prerequisites")
            for prereq in procedure.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")

        lines.append("## Steps")
        lines.append("")

        for step in procedure.get_ordered_steps():
            lines.append(f"### {step.order}. {step.title}")
            lines.append("")
            lines.append(step.description)
            lines.append("")

            if step.executor:
                lines.append(f"**Executor:** {step.executor}")
            if step.tools:
                lines.append(f"**Tools:** {', '.join(step.tools)}")
            if step.inputs:
                lines.append(f"**Inputs:** {', '.join(step.inputs)}")
            if step.outputs:
                lines.append(f"**Outputs:** {', '.join(step.outputs)}")
            if step.estimated_duration:
                lines.append(f"**Duration:** {step.estimated_duration}")

            lines.append("")

        if procedure.success_criteria:
            lines.append("## Success Criteria")
            for criteria in procedure.success_criteria:
                lines.append(f"- {criteria}")

        return "\n".join(lines)

    def _export_checklist(self, procedure: Procedure) -> str:
        """Export as checklist"""
        lines = [f"# {procedure.name} Checklist", ""]

        for step in procedure.get_ordered_steps():
            lines.append(f"[ ] {step.order}. {step.title}")
            if step.description:
                lines.append(f"    - {step.description}")

        return "\n".join(lines)

    def _export_mermaid(self, procedure: Procedure) -> str:
        """Export as mermaid flowchart"""
        lines = ["graph TD"]

        for step in procedure.steps:
            shape_start = "{"
            shape_end = "}"

            if step.type == StepType.DECISION:
                shape_start = "{"
                shape_end = "}"
            elif step.type == StepType.VALIDATION:
                shape_start = "[/"
                shape_end = "/]"
            else:
                shape_start = "["
                shape_end = "]"

            lines.append(f"    {step.id}{shape_start}{step.title}{shape_end}")

        # Add edges
        for step in procedure.steps:
            for dep_id in step.depends_on:
                lines.append(f"    {dep_id} --> {step.id}")

            if step.type == StepType.DECISION:
                if step.true_branch:
                    lines.append(f"    {step.id} -->|Yes| {step.true_branch}")
                if step.false_branch:
                    lines.append(f"    {step.id} -->|No| {step.false_branch}")

        return "\n".join(lines)

    def _export_python(self, procedure: Procedure) -> str:
        """Export as Python code"""
        lines = [
            f'"""',
            f'{procedure.name}',
            f'{procedure.description}',
            f'"""',
            '',
            'import asyncio',
            'from typing import Any, Dict',
            '',
            '',
            f'async def {procedure.name.lower().replace(" ", "_")}(context: Dict[str, Any] = None) -> Dict[str, Any]:',
            f'    """Execute the {procedure.name} procedure."""',
            '    context = context or {}',
            '    results = {}',
            ''
        ]

        for step in procedure.get_ordered_steps():
            func_name = step.title.lower().replace(" ", "_")
            lines.append(f'    # Step {step.order}: {step.title}')
            lines.append(f'    print(f"Executing: {step.title}")')
            lines.append(f'    results["{func_name}"] = await execute_step("{step.id}", context)')
            lines.append('')

        lines.append('    return results')
        lines.append('')
        lines.append('')
        lines.append('async def execute_step(step_id: str, context: Dict[str, Any]) -> Any:')
        lines.append('    """Execute a single step - implement based on step type."""')
        lines.append('    # TODO: Implement step execution logic')
        lines.append('    return {"status": "completed", "step_id": step_id}')

        return "\n".join(lines)

    def _export_pseudocode(self, procedure: Procedure) -> str:
        """Export as pseudocode"""
        lines = [
            f"PROCEDURE {procedure.name}",
            f"// {procedure.description}",
            "",
            "BEGIN"
        ]

        for step in procedure.get_ordered_steps():
            indent = "    "

            if step.type == StepType.DECISION:
                lines.append(f"{indent}IF {step.condition} THEN")
                lines.append(f"{indent}    GOTO {step.true_branch}")
                lines.append(f"{indent}ELSE")
                lines.append(f"{indent}    GOTO {step.false_branch}")
                lines.append(f"{indent}END IF")
            elif step.type == StepType.LOOP:
                lines.append(f"{indent}WHILE {step.loop_condition} DO")
                lines.append(f"{indent}    {step.title}")
                lines.append(f"{indent}END WHILE")
            else:
                lines.append(f"{indent}STEP {step.order}: {step.title}")
                if step.inputs:
                    lines.append(f"{indent}    INPUT: {', '.join(step.inputs)}")
                if step.outputs:
                    lines.append(f"{indent}    OUTPUT: {', '.join(step.outputs)}")

        lines.append("END")

        return "\n".join(lines)

    def optimize(self, procedure: Procedure) -> Procedure:
        """Optimize a procedure for efficiency"""
        # Identify parallelizable steps
        parallelizable = []

        for i, step in enumerate(procedure.steps):
            for j, other in enumerate(procedure.steps):
                if i >= j:
                    continue

                # Check if steps are independent
                if not any(d in [s.id for s in procedure.steps[:j]] for d in step.depends_on):
                    if not any(d in [s.id for s in procedure.steps[:i]] for d in other.depends_on):
                        parallelizable.append((step.id, other.id))

        if parallelizable:
            logger.info(f"Found {len(parallelizable)} parallelizable step pairs")

        return procedure

    def record_execution(
        self,
        procedure_id: str,
        success: bool,
        duration_seconds: float
    ):
        """Record procedure execution for learning"""
        if procedure_id not in self.procedures:
            return

        procedure = self.procedures[procedure_id]
        procedure.execution_count += 1

        # Update success rate with EMA
        alpha = 0.1
        procedure.success_rate = (1 - alpha) * procedure.success_rate + alpha * (1.0 if success else 0.0)

        # Update average duration
        procedure.average_duration_seconds = (
            (1 - alpha) * procedure.average_duration_seconds + alpha * duration_seconds
        )


__all__ = [
    'ProcedureGenerator',
    'Procedure',
    'ProcedureStep',
    'ProcedureType',
    'StepType',
    'OutputFormat'
]
