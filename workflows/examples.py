"""
BAEL - Example Workflows
Pre-built workflow templates for common automation tasks.

Features:
- Code review workflow
- Research workflow
- Content generation workflow
- Data analysis workflow
- DevOps workflow
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW DEFINITIONS
# =============================================================================

class WorkflowCategory(Enum):
    """Workflow categories."""
    DEVELOPMENT = "development"
    RESEARCH = "research"
    CONTENT = "content"
    DATA = "data"
    DEVOPS = "devops"
    AUTOMATION = "automation"


@dataclass
class WorkflowStep:
    """Single workflow step."""
    id: str
    name: str
    description: str
    agent_persona: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 300  # seconds
    retry_count: int = 3


@dataclass
class WorkflowTemplate:
    """Workflow template definition."""
    id: str
    name: str
    description: str
    category: WorkflowCategory
    steps: List[WorkflowStep]
    variables: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    author: str = "BAEL"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "agent_persona": s.agent_persona,
                    "action": s.action,
                    "inputs": s.inputs,
                    "outputs": s.outputs,
                    "depends_on": s.depends_on
                }
                for s in self.steps
            ],
            "variables": self.variables,
            "version": self.version
        }


# =============================================================================
# WORKFLOW TEMPLATES
# =============================================================================

def create_code_review_workflow() -> WorkflowTemplate:
    """Create code review workflow."""
    return WorkflowTemplate(
        id="code_review",
        name="Code Review Pipeline",
        description="Comprehensive code review with security and quality checks",
        category=WorkflowCategory.DEVELOPMENT,
        steps=[
            WorkflowStep(
                id="fetch_code",
                name="Fetch Code",
                description="Fetch code from repository",
                agent_persona="nexus",
                action="fetch_repository",
                inputs={
                    "repo_url": "{{repo_url}}",
                    "branch": "{{branch}}",
                    "pr_number": "{{pr_number}}"
                },
                outputs=["code_files", "diff_content"]
            ),
            WorkflowStep(
                id="static_analysis",
                name="Static Analysis",
                description="Run static code analysis",
                agent_persona="cipher",
                action="analyze_code",
                inputs={
                    "files": "{{code_files}}",
                    "language": "{{language}}"
                },
                outputs=["analysis_results", "issues"],
                depends_on=["fetch_code"]
            ),
            WorkflowStep(
                id="security_scan",
                name="Security Scan",
                description="Check for security vulnerabilities",
                agent_persona="sentinel",
                action="security_scan",
                inputs={
                    "files": "{{code_files}}",
                    "rules": "owasp_top_10"
                },
                outputs=["vulnerabilities", "severity_report"],
                depends_on=["fetch_code"]
            ),
            WorkflowStep(
                id="code_review",
                name="AI Code Review",
                description="Detailed code review by AI",
                agent_persona="nova",
                action="review_code",
                inputs={
                    "diff": "{{diff_content}}",
                    "context": "{{code_files}}",
                    "analysis": "{{analysis_results}}"
                },
                outputs=["review_comments", "suggestions"],
                depends_on=["static_analysis"]
            ),
            WorkflowStep(
                id="generate_report",
                name="Generate Report",
                description="Compile final review report",
                agent_persona="atlas",
                action="generate_report",
                inputs={
                    "review": "{{review_comments}}",
                    "security": "{{vulnerabilities}}",
                    "analysis": "{{analysis_results}}"
                },
                outputs=["final_report"],
                depends_on=["code_review", "security_scan"]
            )
        ],
        variables={
            "repo_url": "",
            "branch": "main",
            "pr_number": "",
            "language": "python"
        }
    )


def create_research_workflow() -> WorkflowTemplate:
    """Create research workflow."""
    return WorkflowTemplate(
        id="research_synthesis",
        name="Research Synthesis Pipeline",
        description="Multi-source research with synthesis and summary",
        category=WorkflowCategory.RESEARCH,
        steps=[
            WorkflowStep(
                id="search_sources",
                name="Search Sources",
                description="Search academic and web sources",
                agent_persona="sage",
                action="search_research",
                inputs={
                    "query": "{{research_topic}}",
                    "sources": ["arxiv", "google_scholar", "semantic_scholar"],
                    "max_results": 20
                },
                outputs=["search_results", "paper_ids"]
            ),
            WorkflowStep(
                id="fetch_papers",
                name="Fetch Papers",
                description="Download and parse research papers",
                agent_persona="nexus",
                action="fetch_papers",
                inputs={
                    "paper_ids": "{{paper_ids}}",
                    "format": "pdf"
                },
                outputs=["paper_contents", "metadata"],
                depends_on=["search_sources"]
            ),
            WorkflowStep(
                id="analyze_papers",
                name="Analyze Papers",
                description="Deep analysis of each paper",
                agent_persona="sage",
                action="analyze_research",
                inputs={
                    "papers": "{{paper_contents}}",
                    "focus_areas": "{{focus_areas}}"
                },
                outputs=["paper_analyses", "key_findings"],
                depends_on=["fetch_papers"]
            ),
            WorkflowStep(
                id="synthesize",
                name="Synthesize Findings",
                description="Synthesize research across all papers",
                agent_persona="sage",
                action="synthesize_research",
                inputs={
                    "analyses": "{{paper_analyses}}",
                    "topic": "{{research_topic}}"
                },
                outputs=["synthesis", "themes", "gaps"],
                depends_on=["analyze_papers"]
            ),
            WorkflowStep(
                id="generate_summary",
                name="Generate Summary",
                description="Create executive summary and report",
                agent_persona="aurora",
                action="write_summary",
                inputs={
                    "synthesis": "{{synthesis}}",
                    "findings": "{{key_findings}}",
                    "format": "{{output_format}}"
                },
                outputs=["summary_report", "citations"],
                depends_on=["synthesize"]
            )
        ],
        variables={
            "research_topic": "",
            "focus_areas": [],
            "output_format": "markdown"
        }
    )


def create_content_generation_workflow() -> WorkflowTemplate:
    """Create content generation workflow."""
    return WorkflowTemplate(
        id="content_generation",
        name="Content Generation Pipeline",
        description="Create blog posts, articles, and documentation",
        category=WorkflowCategory.CONTENT,
        steps=[
            WorkflowStep(
                id="research_topic",
                name="Research Topic",
                description="Research the content topic",
                agent_persona="sage",
                action="research_topic",
                inputs={
                    "topic": "{{topic}}",
                    "keywords": "{{keywords}}",
                    "depth": "comprehensive"
                },
                outputs=["research_notes", "outline_suggestions"]
            ),
            WorkflowStep(
                id="create_outline",
                name="Create Outline",
                description="Create detailed content outline",
                agent_persona="victor",
                action="create_outline",
                inputs={
                    "topic": "{{topic}}",
                    "research": "{{research_notes}}",
                    "target_audience": "{{audience}}",
                    "content_type": "{{content_type}}"
                },
                outputs=["outline", "key_points"],
                depends_on=["research_topic"]
            ),
            WorkflowStep(
                id="write_draft",
                name="Write Draft",
                description="Write initial content draft",
                agent_persona="aurora",
                action="write_content",
                inputs={
                    "outline": "{{outline}}",
                    "tone": "{{tone}}",
                    "word_count": "{{word_count}}"
                },
                outputs=["draft_content"],
                depends_on=["create_outline"]
            ),
            WorkflowStep(
                id="review_edit",
                name="Review & Edit",
                description="Review and improve the draft",
                agent_persona="wisdom",
                action="review_content",
                inputs={
                    "content": "{{draft_content}}",
                    "guidelines": "{{style_guide}}"
                },
                outputs=["edited_content", "feedback"],
                depends_on=["write_draft"]
            ),
            WorkflowStep(
                id="finalize",
                name="Finalize Content",
                description="Final polish and formatting",
                agent_persona="aurora",
                action="finalize_content",
                inputs={
                    "content": "{{edited_content}}",
                    "format": "{{output_format}}",
                    "seo_optimize": True
                },
                outputs=["final_content", "metadata"],
                depends_on=["review_edit"]
            )
        ],
        variables={
            "topic": "",
            "keywords": [],
            "audience": "general",
            "content_type": "blog_post",
            "tone": "professional",
            "word_count": 1500,
            "style_guide": "",
            "output_format": "markdown"
        }
    )


def create_data_analysis_workflow() -> WorkflowTemplate:
    """Create data analysis workflow."""
    return WorkflowTemplate(
        id="data_analysis",
        name="Data Analysis Pipeline",
        description="Analyze datasets and generate insights",
        category=WorkflowCategory.DATA,
        steps=[
            WorkflowStep(
                id="load_data",
                name="Load Data",
                description="Load and validate data sources",
                agent_persona="cipher",
                action="load_dataset",
                inputs={
                    "source": "{{data_source}}",
                    "format": "{{data_format}}",
                    "validate": True
                },
                outputs=["dataset", "schema", "validation_results"]
            ),
            WorkflowStep(
                id="explore_data",
                name="Exploratory Analysis",
                description="Perform exploratory data analysis",
                agent_persona="cipher",
                action="explore_data",
                inputs={
                    "data": "{{dataset}}",
                    "include_visualizations": True
                },
                outputs=["statistics", "distributions", "correlations", "charts"],
                depends_on=["load_data"]
            ),
            WorkflowStep(
                id="clean_data",
                name="Clean Data",
                description="Clean and preprocess data",
                agent_persona="nova",
                action="clean_data",
                inputs={
                    "data": "{{dataset}}",
                    "issues": "{{validation_results}}",
                    "strategy": "{{cleaning_strategy}}"
                },
                outputs=["cleaned_data", "cleaning_log"],
                depends_on=["explore_data"]
            ),
            WorkflowStep(
                id="analyze",
                name="Deep Analysis",
                description="Perform detailed statistical analysis",
                agent_persona="cipher",
                action="statistical_analysis",
                inputs={
                    "data": "{{cleaned_data}}",
                    "analysis_type": "{{analysis_type}}",
                    "hypotheses": "{{hypotheses}}"
                },
                outputs=["analysis_results", "statistical_tests", "models"],
                depends_on=["clean_data"]
            ),
            WorkflowStep(
                id="generate_insights",
                name="Generate Insights",
                description="Extract actionable insights",
                agent_persona="victor",
                action="extract_insights",
                inputs={
                    "analysis": "{{analysis_results}}",
                    "context": "{{business_context}}"
                },
                outputs=["insights", "recommendations"],
                depends_on=["analyze"]
            ),
            WorkflowStep(
                id="create_report",
                name="Create Report",
                description="Generate analysis report",
                agent_persona="aurora",
                action="create_report",
                inputs={
                    "insights": "{{insights}}",
                    "charts": "{{charts}}",
                    "statistics": "{{statistics}}",
                    "format": "{{report_format}}"
                },
                outputs=["report", "dashboard"],
                depends_on=["generate_insights"]
            )
        ],
        variables={
            "data_source": "",
            "data_format": "csv",
            "cleaning_strategy": "auto",
            "analysis_type": "comprehensive",
            "hypotheses": [],
            "business_context": "",
            "report_format": "pdf"
        }
    )


def create_devops_workflow() -> WorkflowTemplate:
    """Create DevOps workflow."""
    return WorkflowTemplate(
        id="devops_pipeline",
        name="DevOps Automation Pipeline",
        description="Build, test, and deploy applications",
        category=WorkflowCategory.DEVOPS,
        steps=[
            WorkflowStep(
                id="checkout",
                name="Checkout Code",
                description="Checkout code from repository",
                agent_persona="nexus",
                action="git_checkout",
                inputs={
                    "repo": "{{repo_url}}",
                    "branch": "{{branch}}",
                    "commit": "{{commit_sha}}"
                },
                outputs=["workspace", "commit_info"]
            ),
            WorkflowStep(
                id="build",
                name="Build Application",
                description="Build the application",
                agent_persona="nova",
                action="build_app",
                inputs={
                    "workspace": "{{workspace}}",
                    "build_command": "{{build_command}}",
                    "environment": "{{build_env}}"
                },
                outputs=["build_artifacts", "build_logs"],
                depends_on=["checkout"]
            ),
            WorkflowStep(
                id="test",
                name="Run Tests",
                description="Execute test suite",
                agent_persona="nova",
                action="run_tests",
                inputs={
                    "workspace": "{{workspace}}",
                    "test_command": "{{test_command}}",
                    "coverage": True
                },
                outputs=["test_results", "coverage_report"],
                depends_on=["build"]
            ),
            WorkflowStep(
                id="security_check",
                name="Security Check",
                description="Run security scans",
                agent_persona="sentinel",
                action="security_scan",
                inputs={
                    "workspace": "{{workspace}}",
                    "artifacts": "{{build_artifacts}}",
                    "scan_type": "full"
                },
                outputs=["security_report", "vulnerabilities"],
                depends_on=["build"]
            ),
            WorkflowStep(
                id="containerize",
                name="Build Container",
                description="Build Docker container",
                agent_persona="nexus",
                action="docker_build",
                inputs={
                    "workspace": "{{workspace}}",
                    "dockerfile": "{{dockerfile}}",
                    "tag": "{{image_tag}}"
                },
                outputs=["image", "image_digest"],
                depends_on=["test", "security_check"]
            ),
            WorkflowStep(
                id="deploy",
                name="Deploy",
                description="Deploy to target environment",
                agent_persona="nexus",
                action="deploy",
                inputs={
                    "image": "{{image}}",
                    "environment": "{{deploy_env}}",
                    "strategy": "{{deploy_strategy}}"
                },
                outputs=["deployment_status", "endpoints"],
                depends_on=["containerize"]
            ),
            WorkflowStep(
                id="verify",
                name="Verify Deployment",
                description="Verify deployment health",
                agent_persona="sentinel",
                action="verify_deployment",
                inputs={
                    "endpoints": "{{endpoints}}",
                    "health_checks": "{{health_checks}}"
                },
                outputs=["verification_results", "metrics"],
                depends_on=["deploy"]
            )
        ],
        variables={
            "repo_url": "",
            "branch": "main",
            "commit_sha": "",
            "build_command": "make build",
            "build_env": {},
            "test_command": "make test",
            "dockerfile": "Dockerfile",
            "image_tag": "latest",
            "deploy_env": "staging",
            "deploy_strategy": "rolling",
            "health_checks": []
        }
    )


# =============================================================================
# WORKFLOW LIBRARY
# =============================================================================

class WorkflowLibrary:
    """Library of pre-built workflows."""

    def __init__(self):
        self._workflows: Dict[str, WorkflowTemplate] = {}
        self._load_built_in_workflows()

    def _load_built_in_workflows(self) -> None:
        """Load built-in workflow templates."""
        workflows = [
            create_code_review_workflow(),
            create_research_workflow(),
            create_content_generation_workflow(),
            create_data_analysis_workflow(),
            create_devops_workflow()
        ]

        for workflow in workflows:
            self._workflows[workflow.id] = workflow

    def get(self, workflow_id: str) -> Optional[WorkflowTemplate]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(
        self,
        category: Optional[WorkflowCategory] = None
    ) -> List[WorkflowTemplate]:
        """List all workflows."""
        workflows = list(self._workflows.values())

        if category:
            workflows = [w for w in workflows if w.category == category]

        return workflows

    def register(self, workflow: WorkflowTemplate) -> None:
        """Register custom workflow."""
        self._workflows[workflow.id] = workflow

    def create_instance(
        self,
        workflow_id: str,
        variables: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create workflow instance with variables."""
        template = self.get(workflow_id)

        if not template:
            return None

        # Merge variables
        merged_vars = {**template.variables, **variables}

        return {
            "id": f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "template_id": workflow_id,
            "name": template.name,
            "variables": merged_vars,
            "steps": [s.id for s in template.steps],
            "created_at": datetime.now().isoformat()
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def main():
    """Demonstrate workflow library."""
    print("=== BAEL Workflow Library ===\n")

    library = WorkflowLibrary()

    # List all workflows
    print("--- Available Workflows ---")
    for workflow in library.list_workflows():
        print(f"\n📋 {workflow.name}")
        print(f"   ID: {workflow.id}")
        print(f"   Category: {workflow.category.value}")
        print(f"   Steps: {len(workflow.steps)}")
        print(f"   Description: {workflow.description}")

    # Show code review workflow details
    print("\n\n--- Code Review Workflow Details ---")
    code_review = library.get("code_review")

    if code_review:
        print(f"\nWorkflow: {code_review.name}")
        print("\nSteps:")
        for i, step in enumerate(code_review.steps, 1):
            deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
            print(f"  {i}. {step.name} [{step.agent_persona}]{deps}")
            print(f"     {step.description}")

        print("\nVariables:")
        for key, value in code_review.variables.items():
            print(f"  - {key}: {value or '(required)'}")

    # Create workflow instance
    print("\n\n--- Create Workflow Instance ---")
    instance = library.create_instance("code_review", {
        "repo_url": "https://github.com/example/repo",
        "branch": "feature/new-feature",
        "pr_number": "42"
    })

    if instance:
        print(f"\nCreated instance: {instance['id']}")
        print(f"Variables: {instance['variables']}")

    # List by category
    print("\n\n--- Development Workflows ---")
    for workflow in library.list_workflows(WorkflowCategory.DEVELOPMENT):
        print(f"  - {workflow.name}")

    print("\n=== Workflow Library ready ===")


if __name__ == "__main__":
    main()
