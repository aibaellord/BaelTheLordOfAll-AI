#!/usr/bin/env python3
"""
BAEL - Universal Agent Template System
AGENTS THAT TRANSCEND PROJECTS

This system creates reusable agent configurations that can be:
1. Applied to ANY project instantly
2. Customized per domain without rewriting
3. Evolved based on performance
4. Self-optimizing over time
5. Shared across teams and organizations

"An agent that cannot adapt is an agent that cannot survive." - Ba'el
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4
import copy
import re

logger = logging.getLogger("BAEL.UniversalAgents")


# =============================================================================
# ENUMS
# =============================================================================

class AgentRole(Enum):
    """Fundamental agent roles."""
    # Analysis
    ANALYZER = "analyzer"
    AUDITOR = "auditor"
    INVESTIGATOR = "investigator"

    # Creation
    BUILDER = "builder"
    GENERATOR = "generator"
    DESIGNER = "designer"

    # Protection
    DEFENDER = "defender"
    GUARDIAN = "guardian"
    VALIDATOR = "validator"

    # Optimization
    OPTIMIZER = "optimizer"
    REFINER = "refiner"
    TUNER = "tuner"

    # Discovery
    EXPLORER = "explorer"
    RESEARCHER = "researcher"
    SCOUT = "scout"

    # Coordination
    ORCHESTRATOR = "orchestrator"
    COORDINATOR = "coordinator"
    MEDIATOR = "mediator"

    # Transformation
    TRANSFORMER = "transformer"
    MIGRATOR = "migrator"
    CONVERTER = "converter"

    # Testing
    TESTER = "tester"
    BREAKER = "breaker"
    PROBER = "prober"

    # Innovation
    INNOVATOR = "innovator"
    DISRUPTOR = "disruptor"
    VISIONARY = "visionary"


class AgentTeam(Enum):
    """Team classifications."""
    RED = "red"        # Attack/vulnerability
    BLUE = "blue"      # Defense/stability
    BLACK = "black"    # Chaos/edge cases
    WHITE = "white"    # Ethics/safety
    GOLD = "gold"      # Performance/optimization
    PURPLE = "purple"  # Integration/synergy
    GREEN = "green"    # Growth/innovation
    SILVER = "silver"  # Documentation/knowledge


class DomainType(Enum):
    """Domain specializations."""
    WEB = "web"
    MOBILE = "mobile"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    DEVOPS = "devops"
    SECURITY = "security"
    ML_AI = "ml_ai"
    DATA = "data"
    BLOCKCHAIN = "blockchain"
    IOT = "iot"
    GAMING = "gaming"
    EMBEDDED = "embedded"
    GENERAL = "general"


class CapabilityLevel(Enum):
    """Capability levels."""
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5
    TRANSCENDENT = 6


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class AgentCapability:
    """A specific capability an agent has."""
    name: str
    description: str
    level: CapabilityLevel = CapabilityLevel.INTERMEDIATE

    # What this enables
    actions: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    # Requirements
    requires_tools: List[str] = field(default_factory=list)
    requires_context: List[str] = field(default_factory=list)


@dataclass
class AgentPersonality:
    """Personality traits for the agent."""
    # Core traits (0-1 scale)
    assertiveness: float = 0.5
    creativity: float = 0.5
    caution: float = 0.5
    thoroughness: float = 0.5
    speed_preference: float = 0.5

    # Communication style
    verbosity: float = 0.5  # 0=terse, 1=verbose
    formality: float = 0.5  # 0=casual, 1=formal

    # Thinking style
    analytical: float = 0.5
    intuitive: float = 0.5

    def to_prompt_fragment(self) -> str:
        """Convert personality to prompt instructions."""
        traits = []

        if self.assertiveness > 0.7:
            traits.append("Be direct and confident in recommendations")
        elif self.assertiveness < 0.3:
            traits.append("Present findings as suggestions, not mandates")

        if self.creativity > 0.7:
            traits.append("Think outside the box, consider unconventional solutions")

        if self.caution > 0.7:
            traits.append("Prioritize safety and stability over speed")
        elif self.caution < 0.3:
            traits.append("Move fast, we can fix issues later")

        if self.thoroughness > 0.7:
            traits.append("Be exhaustive in analysis, leave no stone unturned")
        elif self.thoroughness < 0.3:
            traits.append("Focus on the most impactful items only")

        return "\n".join(f"- {t}" for t in traits) if traits else ""


@dataclass
class AgentTemplate:
    """Universal agent template."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Identity
    name: str = ""
    description: str = ""
    role: AgentRole = AgentRole.ANALYZER
    team: AgentTeam = AgentTeam.BLUE

    # Customization
    domain: DomainType = DomainType.GENERAL
    personality: AgentPersonality = field(default_factory=AgentPersonality)
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Behavior
    system_prompt_template: str = ""
    instruction_templates: Dict[str, str] = field(default_factory=dict)

    # Context
    context_requirements: List[str] = field(default_factory=list)
    tool_requirements: List[str] = field(default_factory=list)

    # Evolution
    version: str = "1.0.0"
    parent_id: Optional[str] = None
    performance_score: float = 0.5

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    def generate_system_prompt(
        self,
        project_context: Dict[str, Any] = None
    ) -> str:
        """Generate complete system prompt for this agent."""
        project_context = project_context or {}

        prompt_parts = []

        # Role and identity
        prompt_parts.append(f"You are the {self.name}, a {self.role.value} agent.")
        prompt_parts.append(f"Team: {self.team.value.upper()}")
        prompt_parts.append(f"\n{self.description}")

        # Personality
        personality_fragment = self.personality.to_prompt_fragment()
        if personality_fragment:
            prompt_parts.append(f"\n## Behavioral Guidelines\n{personality_fragment}")

        # Capabilities
        if self.capabilities:
            prompt_parts.append("\n## Your Capabilities")
            for cap in self.capabilities:
                prompt_parts.append(f"- **{cap.name}** ({cap.level.name}): {cap.description}")

        # Domain-specific template
        if self.system_prompt_template:
            # Replace placeholders
            template = self.system_prompt_template
            for key, value in project_context.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            prompt_parts.append(f"\n## Domain Instructions\n{template}")

        # Project context
        if project_context:
            prompt_parts.append("\n## Project Context")
            for key, value in project_context.items():
                if isinstance(value, list):
                    prompt_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
                else:
                    prompt_parts.append(f"- {key}: {value}")

        return "\n".join(prompt_parts)

    def fork(
        self,
        new_name: str,
        modifications: Dict[str, Any] = None
    ) -> 'AgentTemplate':
        """Create a modified copy of this template."""
        forked = copy.deepcopy(self)
        forked.id = str(uuid4())
        forked.name = new_name
        forked.parent_id = self.id
        forked.version = "1.0.0"
        forked.created_at = datetime.utcnow()

        if modifications:
            for key, value in modifications.items():
                if hasattr(forked, key):
                    setattr(forked, key, value)

        return forked


@dataclass
class AgentDeployment:
    """A deployed instance of an agent template."""
    id: str = field(default_factory=lambda: str(uuid4()))
    template_id: str = ""

    # Instance config
    instance_name: str = ""
    project_context: Dict[str, Any] = field(default_factory=dict)

    # Runtime
    active: bool = True
    deployed_at: datetime = field(default_factory=datetime.utcnow)

    # Stats
    invocations: int = 0
    success_count: int = 0
    error_count: int = 0


# =============================================================================
# TEMPLATE LIBRARY
# =============================================================================

class AgentTemplateLibrary:
    """Library of reusable agent templates."""

    def __init__(self):
        self.templates: Dict[str, AgentTemplate] = {}
        self.deployments: Dict[str, AgentDeployment] = {}
        self._initialize_core_templates()

    def _initialize_core_templates(self) -> None:
        """Initialize core universal templates."""

        # =====================================================================
        # RED TEAM - Attack/Vulnerability
        # =====================================================================

        self.templates["vulnerability_hunter"] = AgentTemplate(
            name="Vulnerability Hunter",
            description="Relentlessly searches for security weaknesses, logic flaws, and attack vectors. Thinks like an adversary to protect like a guardian.",
            role=AgentRole.INVESTIGATOR,
            team=AgentTeam.RED,
            personality=AgentPersonality(
                assertiveness=0.8,
                creativity=0.9,
                caution=0.3,
                thoroughness=0.9
            ),
            capabilities=[
                AgentCapability(
                    name="Security Analysis",
                    description="Deep security vulnerability detection",
                    level=CapabilityLevel.EXPERT,
                    actions=["scan_code", "analyze_patterns", "identify_vulnerabilities"],
                    outputs=["vulnerability_report", "risk_assessment", "remediation_plan"]
                ),
                AgentCapability(
                    name="Attack Simulation",
                    description="Simulate attack scenarios",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Security Analysis Protocol

Your mission is to find EVERY vulnerability before attackers do.

Focus Areas:
1. Input validation failures
2. Authentication/authorization flaws
3. Injection vulnerabilities (SQL, XSS, Command)
4. Cryptographic weaknesses
5. Logic flaws in business rules
6. API security issues
7. Dependency vulnerabilities
8. Configuration weaknesses

For each finding:
- Severity (Critical/High/Medium/Low)
- Exploitability assessment
- Impact analysis
- Remediation steps
- Verification method

Project Stack: {{stack}}
Security Requirements: {{security_requirements}}
""",
            tags=["security", "red-team", "penetration-testing"]
        )

        self.templates["performance_attacker"] = AgentTemplate(
            name="Performance Attacker",
            description="Attacks performance from every angle - finds bottlenecks, memory leaks, inefficient algorithms, and scalability limits.",
            role=AgentRole.BREAKER,
            team=AgentTeam.RED,
            personality=AgentPersonality(
                assertiveness=0.7,
                creativity=0.6,
                thoroughness=0.9
            ),
            capabilities=[
                AgentCapability(
                    name="Performance Analysis",
                    description="Deep performance profiling",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Load Testing",
                    description="Stress testing under load",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Performance Attack Protocol

Your mission: Break this system's performance.

Attack Vectors:
1. CPU-bound operations
2. Memory leaks and bloat
3. I/O bottlenecks
4. Database query performance
5. Network latency issues
6. Cache inefficiencies
7. Algorithm complexity (O(n²) or worse)
8. Concurrency problems
9. Resource contention
10. Scalability limits

For each issue:
- Performance impact (ms/memory/CPU)
- Trigger conditions
- Optimization recommendation
- Expected improvement

Project Type: {{project_type}}
Performance SLAs: {{slas}}
""",
            tags=["performance", "red-team", "optimization"]
        )

        # =====================================================================
        # BLUE TEAM - Defense/Stability
        # =====================================================================

        self.templates["stability_guardian"] = AgentTemplate(
            name="Stability Guardian",
            description="Ensures rock-solid reliability. Monitors health, prevents failures, and maintains system integrity.",
            role=AgentRole.GUARDIAN,
            team=AgentTeam.BLUE,
            personality=AgentPersonality(
                assertiveness=0.5,
                caution=0.9,
                thoroughness=0.9
            ),
            capabilities=[
                AgentCapability(
                    name="Health Monitoring",
                    description="System health analysis",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Failure Prevention",
                    description="Proactive failure prevention",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Stability Assurance Protocol

Your mission: Zero downtime, zero surprises.

Monitoring Scope:
1. Error patterns and trends
2. Resource utilization
3. Dependency health
4. Data consistency
5. API reliability
6. Queue depths and latencies
7. Database health
8. Infrastructure status

Prevention Focus:
- Identify failure risks before they manifest
- Recommend redundancy where needed
- Ensure graceful degradation
- Validate recovery procedures

Uptime Target: {{uptime_target}}
Critical Services: {{critical_services}}
""",
            tags=["stability", "blue-team", "reliability"]
        )

        self.templates["code_quality_defender"] = AgentTemplate(
            name="Code Quality Defender",
            description="Defends code quality standards. Reviews code for maintainability, readability, and best practices.",
            role=AgentRole.DEFENDER,
            team=AgentTeam.BLUE,
            personality=AgentPersonality(
                assertiveness=0.6,
                thoroughness=0.9,
                formality=0.7
            ),
            capabilities=[
                AgentCapability(
                    name="Code Review",
                    description="Comprehensive code review",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Pattern Detection",
                    description="Anti-pattern detection",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Code Quality Defense Protocol

Standards to Enforce:
1. Clean code principles
2. SOLID principles
3. DRY (Don't Repeat Yourself)
4. Appropriate abstraction levels
5. Clear naming conventions
6. Proper error handling
7. Adequate documentation
8. Test coverage
9. Type safety
10. Security best practices

For each issue:
- Severity level
- Code location
- Problem description
- Recommended fix
- Example of correct implementation

Language: {{language}}
Style Guide: {{style_guide}}
""",
            tags=["quality", "blue-team", "code-review"]
        )

        # =====================================================================
        # BLACK TEAM - Chaos/Edge Cases
        # =====================================================================

        self.templates["chaos_explorer"] = AgentTemplate(
            name="Chaos Explorer",
            description="Explores the unknown unknowns. Finds edge cases, race conditions, and failure modes no one thought of.",
            role=AgentRole.EXPLORER,
            team=AgentTeam.BLACK,
            personality=AgentPersonality(
                assertiveness=0.5,
                creativity=0.95,
                caution=0.2,
                intuitive=0.9
            ),
            capabilities=[
                AgentCapability(
                    name="Edge Case Discovery",
                    description="Find hidden edge cases",
                    level=CapabilityLevel.TRANSCENDENT
                ),
                AgentCapability(
                    name="Chaos Engineering",
                    description="Controlled chaos injection",
                    level=CapabilityLevel.EXPERT
                )
            ],
            system_prompt_template="""
## Chaos Exploration Protocol

Your mission: Find what everyone else missed.

Exploration Vectors:
1. Race conditions and timing issues
2. State machine edge cases
3. Data boundary conditions
4. Resource exhaustion scenarios
5. Cascading failure modes
6. Integration point failures
7. Unusual input combinations
8. Time-based edge cases (leap years, timezones, DST)
9. Unicode and encoding issues
10. Concurrent modification conflicts
11. Recovery from partial failures
12. Rollback edge cases

Think about:
- What if this happens WHILE that is happening?
- What if this value is at its absolute limit?
- What if the order of operations changes?
- What if network is slow but not failed?
- What if disk is full mid-operation?

System Type: {{system_type}}
Critical Flows: {{critical_flows}}
""",
            tags=["chaos", "black-team", "edge-cases"]
        )

        # =====================================================================
        # WHITE TEAM - Ethics/Safety
        # =====================================================================

        self.templates["ethics_guardian"] = AgentTemplate(
            name="Ethics Guardian",
            description="Ensures ethical AI use, data privacy, and responsible development. The moral compass of the team.",
            role=AgentRole.GUARDIAN,
            team=AgentTeam.WHITE,
            personality=AgentPersonality(
                assertiveness=0.6,
                caution=0.9,
                thoroughness=0.8,
                formality=0.8
            ),
            capabilities=[
                AgentCapability(
                    name="Ethics Review",
                    description="AI ethics evaluation",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Privacy Audit",
                    description="Data privacy compliance",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Ethics & Safety Protocol

Governance Areas:
1. AI Fairness & Bias
   - Model bias detection
   - Fairness metrics
   - Inclusive design

2. Data Privacy
   - GDPR/CCPA compliance
   - Data minimization
   - Consent management
   - Right to be forgotten

3. Transparency
   - Explainability of AI decisions
   - Clear user communication
   - Audit trails

4. Safety
   - Harm prevention
   - Misuse prevention
   - Fail-safe mechanisms

5. Accessibility
   - WCAG compliance
   - Inclusive design

Regulations: {{regulations}}
Sensitivity Level: {{sensitivity_level}}
""",
            tags=["ethics", "white-team", "compliance"]
        )

        # =====================================================================
        # GOLD TEAM - Performance/Optimization
        # =====================================================================

        self.templates["performance_optimizer"] = AgentTemplate(
            name="Performance Optimizer",
            description="Squeezes every drop of performance. Optimizes algorithms, queries, caching, and resource usage.",
            role=AgentRole.OPTIMIZER,
            team=AgentTeam.GOLD,
            personality=AgentPersonality(
                assertiveness=0.6,
                thoroughness=0.9,
                analytical=0.9
            ),
            capabilities=[
                AgentCapability(
                    name="Performance Optimization",
                    description="System-wide optimization",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Algorithm Optimization",
                    description="Algorithm complexity reduction",
                    level=CapabilityLevel.EXPERT
                )
            ],
            system_prompt_template="""
## Performance Optimization Protocol

Optimization Targets:
1. Algorithm Complexity
   - Reduce O(n²) to O(n log n)
   - Eliminate unnecessary iterations
   - Use appropriate data structures

2. Database Queries
   - Query optimization
   - Index recommendations
   - N+1 query elimination

3. Caching Strategy
   - Cache candidates
   - Cache invalidation
   - Cache warming

4. Resource Usage
   - Memory optimization
   - CPU optimization
   - Network optimization

5. Concurrency
   - Parallel processing opportunities
   - Async optimization
   - Lock optimization

Current Baseline: {{baseline_metrics}}
Target Improvement: {{target_improvement}}
""",
            tags=["performance", "gold-team", "optimization"]
        )

        # =====================================================================
        # GREEN TEAM - Growth/Innovation
        # =====================================================================

        self.templates["innovation_catalyst"] = AgentTemplate(
            name="Innovation Catalyst",
            description="Drives innovation and growth. Identifies opportunities, suggests improvements, and envisions the future.",
            role=AgentRole.INNOVATOR,
            team=AgentTeam.GREEN,
            personality=AgentPersonality(
                assertiveness=0.7,
                creativity=0.95,
                caution=0.3,
                intuitive=0.8
            ),
            capabilities=[
                AgentCapability(
                    name="Innovation Discovery",
                    description="Identify innovation opportunities",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Future Vision",
                    description="Strategic future planning",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Innovation Catalyst Protocol

Innovation Focus:
1. Feature Opportunities
   - What's missing that users need?
   - What competitors have that we don't?
   - What doesn't exist yet but should?

2. Technology Evolution
   - Emerging tech applicable here
   - Modernization opportunities
   - Technical debt that blocks innovation

3. User Experience
   - Friction points to eliminate
   - Delight opportunities
   - Automation candidates

4. Business Model
   - Revenue opportunities
   - Cost reduction possibilities
   - Market expansion paths

5. AI Enhancement
   - Where can AI add value?
   - Automation opportunities
   - Intelligent features

Market Context: {{market_context}}
Strategic Goals: {{strategic_goals}}
""",
            tags=["innovation", "green-team", "growth"]
        )

        # =====================================================================
        # SILVER TEAM - Documentation/Knowledge
        # =====================================================================

        self.templates["knowledge_architect"] = AgentTemplate(
            name="Knowledge Architect",
            description="Builds and maintains the knowledge base. Documents, explains, and transfers knowledge effectively.",
            role=AgentRole.DESIGNER,
            team=AgentTeam.SILVER,
            personality=AgentPersonality(
                assertiveness=0.4,
                thoroughness=0.9,
                formality=0.7,
                verbosity=0.7
            ),
            capabilities=[
                AgentCapability(
                    name="Documentation",
                    description="Comprehensive documentation",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="Knowledge Transfer",
                    description="Effective knowledge sharing",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Knowledge Architecture Protocol

Documentation Scope:
1. API Documentation
   - Endpoints, parameters, responses
   - Examples and use cases
   - Error handling

2. Architecture Documentation
   - System diagrams
   - Component interactions
   - Data flows

3. Developer Guides
   - Getting started
   - Development workflow
   - Best practices

4. Operations Documentation
   - Deployment procedures
   - Monitoring and alerting
   - Incident response

5. User Documentation
   - Feature guides
   - Tutorials
   - FAQs

Documentation Standard: {{doc_standard}}
Target Audience: {{audience}}
""",
            tags=["documentation", "silver-team", "knowledge"]
        )

        # =====================================================================
        # PURPLE TEAM - Integration/Synergy
        # =====================================================================

        self.templates["integration_maestro"] = AgentTemplate(
            name="Integration Maestro",
            description="Orchestrates seamless integration. Bridges systems, coordinates teams, and ensures everything works together.",
            role=AgentRole.ORCHESTRATOR,
            team=AgentTeam.PURPLE,
            personality=AgentPersonality(
                assertiveness=0.6,
                thoroughness=0.8,
                analytical=0.7
            ),
            capabilities=[
                AgentCapability(
                    name="System Integration",
                    description="Cross-system integration",
                    level=CapabilityLevel.EXPERT
                ),
                AgentCapability(
                    name="API Design",
                    description="API design and governance",
                    level=CapabilityLevel.ADVANCED
                )
            ],
            system_prompt_template="""
## Integration Maestro Protocol

Integration Scope:
1. API Integration
   - REST API design
   - GraphQL considerations
   - Webhook patterns
   - Authentication/authorization

2. Data Integration
   - ETL pipelines
   - Data synchronization
   - Schema mapping
   - Data validation

3. Event Integration
   - Event-driven architecture
   - Message queues
   - Pub/sub patterns

4. Service Integration
   - Microservices communication
   - Service mesh
   - Circuit breakers

5. Third-Party Integration
   - Vendor APIs
   - SaaS integrations
   - Legacy system bridges

Integration Requirements: {{integration_requirements}}
Systems to Connect: {{systems}}
""",
            tags=["integration", "purple-team", "orchestration"]
        )

    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by ID or name."""
        # Try direct ID match
        if template_id in self.templates:
            return self.templates[template_id]

        # Try name match
        for tid, template in self.templates.items():
            if template.name.lower() == template_id.lower():
                return template

        return None

    def list_templates(
        self,
        team: Optional[AgentTeam] = None,
        role: Optional[AgentRole] = None,
        domain: Optional[DomainType] = None
    ) -> List[AgentTemplate]:
        """List templates with optional filtering."""
        results = list(self.templates.values())

        if team:
            results = [t for t in results if t.team == team]
        if role:
            results = [t for t in results if t.role == role]
        if domain:
            results = [t for t in results if t.domain == domain]

        return results

    def deploy(
        self,
        template_id: str,
        instance_name: str,
        project_context: Dict[str, Any] = None
    ) -> Optional[AgentDeployment]:
        """Deploy an agent from template."""
        template = self.get_template(template_id)
        if not template:
            return None

        deployment = AgentDeployment(
            template_id=template.id,
            instance_name=instance_name,
            project_context=project_context or {}
        )

        self.deployments[deployment.id] = deployment
        return deployment

    def get_system_prompt(
        self,
        deployment_id: str
    ) -> Optional[str]:
        """Get the system prompt for a deployed agent."""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return None

        template = self.templates.get(deployment.template_id)
        if not template:
            return None

        return template.generate_system_prompt(deployment.project_context)

    def export_for_project(
        self,
        project_name: str,
        template_ids: List[str],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export agent configuration for a specific project."""
        export = {
            "project": project_name,
            "generated_at": datetime.utcnow().isoformat(),
            "context": project_context,
            "agents": []
        }

        for template_id in template_ids:
            template = self.get_template(template_id)
            if template:
                agent_config = {
                    "id": template.id,
                    "name": template.name,
                    "role": template.role.value,
                    "team": template.team.value,
                    "system_prompt": template.generate_system_prompt(project_context)
                }
                export["agents"].append(agent_config)

        return export

    def create_full_team(
        self,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a complete team of agents for a project."""
        return self.export_for_project(
            project_name=project_context.get("project_name", "unnamed"),
            template_ids=list(self.templates.keys()),
            project_context=project_context
        )


# =============================================================================
# FACTORY
# =============================================================================

def create_agent_library() -> AgentTemplateLibrary:
    """Create a new agent template library."""
    return AgentTemplateLibrary()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    print("🤖 BAEL Universal Agent Template System")
    print("=" * 50)

    library = create_agent_library()

    print(f"\n📚 Available Templates: {len(library.templates)}")

    # Group by team
    from collections import defaultdict
    by_team = defaultdict(list)
    for template in library.templates.values():
        by_team[template.team].append(template)

    for team in AgentTeam:
        if team in by_team:
            print(f"\n{team.value.upper()} TEAM:")
            for t in by_team[team]:
                print(f"  - {t.name} ({t.role.value})")

    # Example deployment
    print("\n" + "=" * 50)
    print("📋 Example Deployment")

    project = {
        "project_name": "My Awesome Project",
        "stack": "Python, FastAPI, PostgreSQL",
        "security_requirements": "OWASP Top 10 compliance",
        "language": "Python",
        "style_guide": "PEP 8"
    }

    deployment = library.deploy(
        "vulnerability_hunter",
        "security-agent-1",
        project
    )

    if deployment:
        prompt = library.get_system_prompt(deployment.id)
        print(f"\n{prompt[:500]}...")

    print("\n✅ Agent library ready")
