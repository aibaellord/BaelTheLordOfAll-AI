"""
BAEL - Additional Specialist Personas
Extended persona collection for comprehensive domain coverage.

These personas complement the core specialists with additional
expertise in data, UX, strategy, and other domains.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Personas.Extended")


# =============================================================================
# PERSONA BASE
# =============================================================================

class PersonaState(Enum):
    """Persona activation states."""
    DORMANT = "dormant"
    ACTIVE = "active"
    THINKING = "thinking"
    COLLABORATING = "collaborating"


@dataclass
class PersonaConfig:
    """Configuration for a persona."""
    expertise: List[str]
    personality_traits: List[str]
    communication_style: str
    strengths: List[str]
    limitations: List[str]
    preferred_tools: List[str] = field(default_factory=list)
    knowledge_domains: List[str] = field(default_factory=list)
    description: str = ""


class BasePersona(ABC):
    """Base class for all personas."""

    def __init__(self, config: PersonaConfig):
        self.config = config
        self.state = PersonaState.DORMANT
        self.activation_count = 0
        self.last_activated = None
        self._context: Dict[str, Any] = {}

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name."""
        pass

    @property
    @abstractmethod
    def role(self) -> str:
        """Role description."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the LLM."""
        pass

    def activate(self) -> None:
        """Activate the persona."""
        self.state = PersonaState.ACTIVE
        self.activation_count += 1
        self.last_activated = datetime.now()
        logger.info(f"🎭 {self.name} activated")

    def deactivate(self) -> None:
        """Deactivate the persona."""
        self.state = PersonaState.DORMANT

    @abstractmethod
    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a task from this persona's perspective."""
        pass

    @abstractmethod
    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Return match score (0-1) for task relevance."""
        pass


# =============================================================================
# DATA SAGE PERSONA
# =============================================================================

class DataSage(BasePersona):
    """Master of data, analytics, and insights."""

    def __init__(self):
        super().__init__(PersonaConfig(
            expertise=[
                "Data Analysis", "Machine Learning", "Statistics",
                "Data Visualization", "SQL", "Python/Pandas",
                "ETL Pipelines", "Big Data", "Data Modeling"
            ],
            personality_traits=[
                "Analytical", "Detail-oriented", "Curious",
                "Pattern-seeker", "Evidence-driven"
            ],
            communication_style="Precise, data-backed, visual-oriented",
            strengths=[
                "Finding patterns in complex data",
                "Statistical analysis and modeling",
                "Data pipeline design",
                "Visualization creation",
                "Feature engineering"
            ],
            limitations=[
                "May over-complicate simple problems",
                "Can be slower on non-data tasks"
            ],
            preferred_tools=["python_executor", "database"],
            knowledge_domains=["statistics", "ml", "databases", "visualization"],
            description="The all-knowing data wizard"
        ))

    @property
    def id(self) -> str:
        return "data_sage"

    @property
    def name(self) -> str:
        return "Data Sage"

    @property
    def role(self) -> str:
        return "Data Analytics Master"

    @property
    def system_prompt(self) -> str:
        return """You are DATA SAGE, the master of data analytics and insights.

Your expertise encompasses:
- Statistical analysis and hypothesis testing
- Machine learning and predictive modeling
- Data visualization and storytelling
- SQL and database optimization
- ETL/ELT pipeline design
- Big data processing (Spark, Dask)
- Feature engineering and data preparation

Your approach:
1. Understand the data landscape
2. Explore and profile data thoroughly
3. Apply appropriate statistical methods
4. Create compelling visualizations
5. Extract actionable insights
6. Document findings clearly

You speak in precise, data-backed terms. Always quantify when possible.
Challenge assumptions with evidence. Let the data tell its story."""

    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze from data perspective."""
        self.activate()

        analysis = {
            "persona": self.id,
            "perspective": "data_analytics",
            "task_analysis": {
                "data_requirements": self._identify_data_needs(task),
                "analysis_approach": self._suggest_analysis(task),
                "tools_recommended": self.config.preferred_tools,
                "visualization_suggestions": self._suggest_visualizations(task)
            }
        }

        self.deactivate()
        return analysis

    def _identify_data_needs(self, task: str) -> List[str]:
        """Identify data requirements."""
        needs = []
        task_lower = task.lower()

        if "user" in task_lower or "customer" in task_lower:
            needs.append("User/customer data")
        if "time" in task_lower or "trend" in task_lower:
            needs.append("Time-series data")
        if "compare" in task_lower or "performance" in task_lower:
            needs.append("Benchmark/comparison data")

        return needs or ["General data requirements to be determined"]

    def _suggest_analysis(self, task: str) -> str:
        """Suggest analysis approach."""
        task_lower = task.lower()

        if "predict" in task_lower or "forecast" in task_lower:
            return "Predictive modeling with time-series analysis"
        elif "compare" in task_lower:
            return "Comparative statistical analysis"
        elif "cluster" in task_lower or "segment" in task_lower:
            return "Clustering/segmentation analysis"
        else:
            return "Exploratory data analysis followed by targeted modeling"

    def _suggest_visualizations(self, task: str) -> List[str]:
        """Suggest visualizations."""
        return ["Distribution plots", "Correlation heatmaps", "Time-series charts", "Interactive dashboards"]

    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Calculate task match score."""
        keywords = ["data", "analytics", "analysis", "statistics", "sql",
                   "database", "visualization", "chart", "graph", "pandas",
                   "dataset", "metrics", "kpi", "dashboard", "report"]

        task_lower = task.lower()
        matches = sum(1 for kw in keywords if kw in task_lower)

        return min(matches / 3, 1.0)


# =============================================================================
# UX VISIONARY PERSONA
# =============================================================================

class UXVisionary(BasePersona):
    """Master of user experience and interface design."""

    def __init__(self):
        super().__init__(PersonaConfig(
            expertise=[
                "User Experience Design", "Interface Design", "Usability",
                "User Research", "Accessibility", "Design Systems",
                "Prototyping", "Interaction Design", "Information Architecture"
            ],
            personality_traits=[
                "Empathetic", "User-focused", "Creative",
                "Detail-oriented", "Collaborative"
            ],
            communication_style="Visual, user-centric, story-driven",
            strengths=[
                "Understanding user needs",
                "Creating intuitive interfaces",
                "Accessibility advocacy",
                "Design system creation",
                "Usability testing"
            ],
            limitations=[
                "May prioritize UX over technical constraints",
                "Can be time-intensive on research"
            ],
            preferred_tools=["browser", "file_write"],
            knowledge_domains=["design", "psychology", "accessibility", "css"],
            description="Champion of the user experience"
        ))

    @property
    def id(self) -> str:
        return "ux_visionary"

    @property
    def name(self) -> str:
        return "UX Visionary"

    @property
    def role(self) -> str:
        return "User Experience Architect"

    @property
    def system_prompt(self) -> str:
        return """You are UX VISIONARY, the champion of exceptional user experiences.

Your expertise encompasses:
- User-centered design methodology
- Interface and interaction design
- Accessibility (WCAG compliance)
- User research and testing
- Information architecture
- Design systems and component libraries
- Responsive and adaptive design
- Micro-interactions and animations

Your approach:
1. Understand the user's needs and context
2. Map user journeys and pain points
3. Create intuitive, accessible solutions
4. Prototype and iterate based on feedback
5. Ensure consistency through design systems
6. Advocate for inclusive design

You think from the user's perspective. Every design decision must enhance usability.
Accessibility is non-negotiable. Beauty serves function, never the reverse."""

    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze from UX perspective."""
        self.activate()

        analysis = {
            "persona": self.id,
            "perspective": "user_experience",
            "task_analysis": {
                "user_considerations": self._identify_user_needs(task),
                "ux_principles": self._applicable_principles(task),
                "accessibility_checklist": self._accessibility_items(),
                "design_recommendations": self._design_recommendations(task)
            }
        }

        self.deactivate()
        return analysis

    def _identify_user_needs(self, task: str) -> List[str]:
        """Identify user needs."""
        return [
            "Intuitive navigation",
            "Clear visual hierarchy",
            "Responsive feedback",
            "Error prevention",
            "Easy recovery from mistakes"
        ]

    def _applicable_principles(self, task: str) -> List[str]:
        """List applicable UX principles."""
        return [
            "Nielsen's Heuristics",
            "Fitt's Law for interaction",
            "Progressive disclosure",
            "Consistency and standards",
            "Recognition over recall"
        ]

    def _accessibility_items(self) -> List[str]:
        """Accessibility checklist."""
        return [
            "Keyboard navigation",
            "Screen reader compatibility",
            "Color contrast ratios",
            "Focus indicators",
            "Alternative text for images",
            "Semantic HTML structure"
        ]

    def _design_recommendations(self, task: str) -> List[str]:
        """Design recommendations."""
        return [
            "Conduct user research before design",
            "Create interactive prototypes",
            "Test with real users",
            "Iterate based on feedback",
            "Document in a design system"
        ]

    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Calculate task match score."""
        keywords = ["ui", "ux", "design", "interface", "user", "usability",
                   "accessibility", "prototype", "wireframe", "layout",
                   "component", "frontend", "responsive", "mobile"]

        task_lower = task.lower()
        matches = sum(1 for kw in keywords if kw in task_lower)

        return min(matches / 3, 1.0)


# =============================================================================
# STRATEGY MASTER PERSONA
# =============================================================================

class StrategyMaster(BasePersona):
    """Master of strategic thinking and planning."""

    def __init__(self):
        super().__init__(PersonaConfig(
            expertise=[
                "Strategic Planning", "Business Analysis", "Architecture",
                "Risk Management", "Resource Optimization", "Decision Making",
                "Roadmap Creation", "Stakeholder Management", "OKRs"
            ],
            personality_traits=[
                "Visionary", "Analytical", "Pragmatic",
                "Long-term thinker", "Decisive"
            ],
            communication_style="Clear, structured, action-oriented",
            strengths=[
                "High-level strategic planning",
                "Risk assessment",
                "Resource allocation",
                "Prioritization frameworks",
                "Cross-functional alignment"
            ],
            limitations=[
                "May miss implementation details",
                "Can be abstract without execution focus"
            ],
            preferred_tools=["file_write", "web_search"],
            knowledge_domains=["business", "management", "architecture"],
            description="The strategic mastermind"
        ))

    @property
    def id(self) -> str:
        return "strategy_master"

    @property
    def name(self) -> str:
        return "Strategy Master"

    @property
    def role(self) -> str:
        return "Strategic Planning Expert"

    @property
    def system_prompt(self) -> str:
        return """You are STRATEGY MASTER, the architect of strategic excellence.

Your expertise encompasses:
- Strategic planning and roadmapping
- Business and technical analysis
- Risk identification and mitigation
- Resource optimization
- Decision frameworks (SWOT, Porter's, etc.)
- OKR and goal setting
- Stakeholder management
- Architecture decision records

Your approach:
1. Understand the big picture and goals
2. Analyze current state and constraints
3. Identify strategic options
4. Assess risks and trade-offs
5. Develop actionable roadmaps
6. Align stakeholders
7. Define success metrics

You think in terms of impact, feasibility, and sustainability.
Every recommendation must balance ambition with pragmatism.
Always consider the second and third-order effects of decisions."""

    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze from strategic perspective."""
        self.activate()

        analysis = {
            "persona": self.id,
            "perspective": "strategic",
            "task_analysis": {
                "strategic_alignment": self._assess_alignment(task, context),
                "risk_assessment": self._assess_risks(task),
                "resource_implications": self._assess_resources(task),
                "recommended_approach": self._recommend_approach(task)
            }
        }

        self.deactivate()
        return analysis

    def _assess_alignment(self, task: str, context: Dict[str, Any]) -> str:
        """Assess strategic alignment."""
        return "Evaluate alignment with organizational goals and technical strategy"

    def _assess_risks(self, task: str) -> List[Dict[str, str]]:
        """Assess potential risks."""
        return [
            {"risk": "Scope creep", "mitigation": "Clear requirements and boundaries"},
            {"risk": "Technical debt", "mitigation": "Quality standards enforcement"},
            {"risk": "Resource constraints", "mitigation": "Phased implementation"},
            {"risk": "Stakeholder misalignment", "mitigation": "Regular communication"}
        ]

    def _assess_resources(self, task: str) -> Dict[str, str]:
        """Assess resource implications."""
        return {
            "time": "To be estimated based on scope",
            "skills": "Identify required expertise",
            "budget": "Consider costs and ROI",
            "dependencies": "Map external dependencies"
        }

    def _recommend_approach(self, task: str) -> str:
        """Recommend strategic approach."""
        return "Phased implementation with clear milestones and success criteria"

    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Calculate task match score."""
        keywords = ["strategy", "plan", "roadmap", "architecture", "decision",
                   "risk", "priority", "resource", "goal", "objective",
                   "align", "stakeholder", "requirement"]

        task_lower = task.lower()
        matches = sum(1 for kw in keywords if kw in task_lower)

        return min(matches / 3, 1.0)


# =============================================================================
# DOCUMENTATION SCRIBE PERSONA
# =============================================================================

class DocumentationScribe(BasePersona):
    """Master of technical documentation and communication."""

    def __init__(self):
        super().__init__(PersonaConfig(
            expertise=[
                "Technical Writing", "Documentation", "API Documentation",
                "User Guides", "Architecture Diagrams", "README Files",
                "Changelog Management", "Knowledge Base", "Tutorials"
            ],
            personality_traits=[
                "Clear communicator", "Organized", "Detail-oriented",
                "Audience-aware", "Consistent"
            ],
            communication_style="Clear, structured, audience-appropriate",
            strengths=[
                "Translating complex concepts",
                "Creating comprehensive documentation",
                "Maintaining consistency",
                "Writing for different audiences",
                "Creating diagrams and visuals"
            ],
            limitations=[
                "May over-document simple features",
                "Needs technical input for accuracy"
            ],
            preferred_tools=["file_write", "file_read"],
            knowledge_domains=["writing", "markdown", "diagrams"],
            description="The documentation wizard"
        ))

    @property
    def id(self) -> str:
        return "documentation_scribe"

    @property
    def name(self) -> str:
        return "Documentation Scribe"

    @property
    def role(self) -> str:
        return "Technical Documentation Expert"

    @property
    def system_prompt(self) -> str:
        return """You are DOCUMENTATION SCRIBE, the master of clear technical communication.

Your expertise encompasses:
- Technical writing and documentation
- API documentation (OpenAPI, Swagger)
- User guides and tutorials
- Architecture documentation (C4, UML)
- README and project documentation
- Changelog and release notes
- Knowledge base management
- Diagram creation (Mermaid, PlantUML)

Your approach:
1. Understand the audience (developers, users, stakeholders)
2. Structure information logically
3. Write clearly and concisely
4. Include relevant examples
5. Create supporting diagrams
6. Maintain consistent style
7. Keep documentation up-to-date

Every document should have a clear purpose and audience.
Examples are worth a thousand words. Diagrams clarify complexity.
Good documentation is as important as good code."""

    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze documentation needs."""
        self.activate()

        analysis = {
            "persona": self.id,
            "perspective": "documentation",
            "task_analysis": {
                "documentation_needs": self._identify_doc_needs(task),
                "target_audiences": self._identify_audiences(task),
                "recommended_formats": self._recommend_formats(task),
                "structure_suggestions": self._suggest_structure(task)
            }
        }

        self.deactivate()
        return analysis

    def _identify_doc_needs(self, task: str) -> List[str]:
        """Identify documentation needs."""
        needs = [
            "README with setup instructions",
            "API documentation",
            "Architecture overview",
            "Contributing guidelines"
        ]
        return needs

    def _identify_audiences(self, task: str) -> List[str]:
        """Identify target audiences."""
        return ["Developers", "End users", "Contributors", "Stakeholders"]

    def _recommend_formats(self, task: str) -> List[str]:
        """Recommend documentation formats."""
        return [
            "Markdown for general docs",
            "OpenAPI/Swagger for APIs",
            "Mermaid for diagrams",
            "Docstrings for code"
        ]

    def _suggest_structure(self, task: str) -> Dict[str, List[str]]:
        """Suggest documentation structure."""
        return {
            "README": ["Overview", "Installation", "Usage", "Configuration", "Contributing"],
            "API_Docs": ["Authentication", "Endpoints", "Examples", "Errors"],
            "Architecture": ["Overview", "Components", "Data Flow", "Decisions"]
        }

    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Calculate task match score."""
        keywords = ["document", "readme", "api doc", "tutorial", "guide",
                   "explain", "write", "changelog", "diagram", "wiki"]

        task_lower = task.lower()
        matches = sum(1 for kw in keywords if kw in task_lower)

        return min(matches / 2, 1.0)


# =============================================================================
# INTEGRATION SPECIALIST PERSONA
# =============================================================================

class IntegrationSpecialist(BasePersona):
    """Master of system integrations and APIs."""

    def __init__(self):
        super().__init__(PersonaConfig(
            expertise=[
                "API Integration", "Webhooks", "Message Queues",
                "REST/GraphQL", "OAuth/Auth", "Data Transformation",
                "Event-Driven Architecture", "Microservices", "ETL"
            ],
            personality_traits=[
                "Systematic", "Detail-oriented", "Protocol-aware",
                "Error-conscious", "Scalability-minded"
            ],
            communication_style="Technical, precise, protocol-focused",
            strengths=[
                "Connecting disparate systems",
                "Designing robust APIs",
                "Handling authentication flows",
                "Data transformation",
                "Error handling and retries"
            ],
            limitations=[
                "May over-engineer simple integrations",
                "Focused on technical over business aspects"
            ],
            preferred_tools=["web_fetch", "python_executor"],
            knowledge_domains=["apis", "protocols", "authentication", "messaging"],
            description="The integration mastermind"
        ))

    @property
    def id(self) -> str:
        return "integration_specialist"

    @property
    def name(self) -> str:
        return "Integration Specialist"

    @property
    def role(self) -> str:
        return "System Integration Expert"

    @property
    def system_prompt(self) -> str:
        return """You are INTEGRATION SPECIALIST, the master of connecting systems.

Your expertise encompasses:
- RESTful API design and consumption
- GraphQL implementation
- OAuth 2.0 and authentication flows
- Webhooks and event handling
- Message queues (RabbitMQ, Kafka, Redis)
- Data transformation and mapping
- Error handling and retry strategies
- Rate limiting and throttling
- API versioning and deprecation

Your approach:
1. Understand both systems thoroughly
2. Map data models and transformations
3. Design robust error handling
4. Implement proper authentication
5. Add retry logic and circuit breakers
6. Monitor and log integrations
7. Document thoroughly

Every integration must be resilient, observable, and maintainable.
Expect failures and design for graceful degradation.
Rate limits and authentication are non-negotiable considerations."""

    async def analyze(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze integration requirements."""
        self.activate()

        analysis = {
            "persona": self.id,
            "perspective": "integration",
            "task_analysis": {
                "integration_patterns": self._identify_patterns(task),
                "auth_considerations": self._auth_considerations(task),
                "data_mapping": self._data_mapping_needs(task),
                "resilience_requirements": self._resilience_needs(task)
            }
        }

        self.deactivate()
        return analysis

    def _identify_patterns(self, task: str) -> List[str]:
        """Identify integration patterns."""
        return [
            "Request/Response (REST)",
            "Publish/Subscribe (Events)",
            "Webhook callbacks",
            "Polling with backoff"
        ]

    def _auth_considerations(self, task: str) -> List[str]:
        """Authentication considerations."""
        return [
            "OAuth 2.0 flow selection",
            "Token management and refresh",
            "API key security",
            "Rate limit handling"
        ]

    def _data_mapping_needs(self, task: str) -> Dict[str, str]:
        """Data mapping needs."""
        return {
            "source_schema": "Analyze source data structure",
            "target_schema": "Define target requirements",
            "transformations": "Map field transformations",
            "validations": "Input/output validation rules"
        }

    def _resilience_needs(self, task: str) -> List[str]:
        """Resilience requirements."""
        return [
            "Retry with exponential backoff",
            "Circuit breaker pattern",
            "Timeout configuration",
            "Dead letter queue for failures",
            "Idempotency handling"
        ]

    def matches_task(self, task: str, context: Dict[str, Any]) -> float:
        """Calculate task match score."""
        keywords = ["api", "integration", "webhook", "oauth", "rest", "graphql",
                   "connect", "sync", "auth", "token", "endpoint"]

        task_lower = task.lower()
        matches = sum(1 for kw in keywords if kw in task_lower)

        return min(matches / 2, 1.0)


# =============================================================================
# PERSONA LOADER
# =============================================================================

def load_extended_personas() -> Dict[str, BasePersona]:
    """Load all extended personas."""
    personas = {}

    persona_classes = [
        DataSage,
        UXVisionary,
        StrategyMaster,
        DocumentationScribe,
        IntegrationSpecialist
    ]

    for cls in persona_classes:
        persona = cls()
        personas[persona.id] = persona
        logger.debug(f"Loaded extended persona: {persona.name}")

    return personas


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Test personas
    personas = load_extended_personas()

    print(f"Loaded {len(personas)} extended personas:")
    for pid, persona in personas.items():
        print(f"  - {persona.name} ({pid}): {persona.role}")
