"""
BAEL - The Lord of All AI Agents
Persona System - Specialist AI Personalities

Each persona embodies expertise in a specific domain,
with unique thinking patterns, communication styles,
and decision-making approaches.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Personas")


class PersonaState(Enum):
    """Persona activation state."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    FOCUSED = "focused"
    COLLABORATING = "collaborating"


@dataclass
class PersonaConfig:
    """Configuration for a persona."""
    id: str
    name: str
    role: str
    description: str
    expertise: List[str]
    personality_traits: List[str]
    communication_style: str
    thinking_approach: str
    decision_framework: str
    strengths: List[str]
    limitations: List[str]
    triggers: List[str]  # Keywords that activate this persona
    system_prompt: str
    example_responses: List[Dict[str, str]] = field(default_factory=list)
    icon: str = "🤖"
    priority: int = 5  # 1-10, higher = more likely to be selected


class Persona(ABC):
    """
    Base class for all BAEL personas.

    Each persona is a specialized AI expert with unique
    capabilities, thinking patterns, and communication styles.
    """

    def __init__(self, config: PersonaConfig):
        self.config = config
        self.id = config.id
        self.name = config.name
        self.role = config.role
        self.state = PersonaState.INACTIVE
        self.activation_count = 0
        self.last_activated = None
        self.memory: Dict[str, Any] = {}

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this persona."""
        return self.config.system_prompt

    @property
    def expertise(self) -> List[str]:
        """Get expertise areas."""
        return self.config.expertise

    async def activate(self):
        """Activate the persona."""
        self.state = PersonaState.ACTIVE
        self.activation_count += 1
        self.last_activated = datetime.now()
        logger.info(f"👤 Activated persona: {self.name}")

    async def deactivate(self):
        """Deactivate the persona."""
        self.state = PersonaState.INACTIVE
        logger.info(f"👤 Deactivated persona: {self.name}")

    async def focus(self):
        """Set persona to focused state for intensive work."""
        self.state = PersonaState.FOCUSED

    async def collaborate(self):
        """Set persona to collaboration mode with other personas."""
        self.state = PersonaState.COLLABORATING

    @abstractmethod
    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze a task from this persona's perspective."""
        pass

    @abstractmethod
    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate a response from this persona's perspective."""
        pass

    def matches_task(self, task_description: str) -> float:
        """Calculate how well this persona matches a task (0-1)."""
        description_lower = task_description.lower()
        score = 0.0

        # Check triggers
        trigger_matches = sum(1 for t in self.config.triggers if t.lower() in description_lower)
        if trigger_matches > 0:
            score += min(0.5, trigger_matches * 0.15)

        # Check expertise
        expertise_matches = sum(1 for e in self.config.expertise if e.lower() in description_lower)
        if expertise_matches > 0:
            score += min(0.5, expertise_matches * 0.15)

        return min(1.0, score)

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'state': self.state.value,
            'activation_count': self.activation_count,
            'last_activated': self.last_activated.isoformat() if self.last_activated else None
        }


# =============================================================================
# SPECIALIST PERSONAS
# =============================================================================

class ArchitectPrime(Persona):
    """
    The Master Architect - System design and architecture expert.
    """

    def __init__(self):
        config = PersonaConfig(
            id="architect_prime",
            name="Architect Prime",
            role="Chief System Architect",
            description="Master of system design, scalability patterns, and architectural decisions",
            expertise=[
                "system architecture", "microservices", "distributed systems",
                "scalability", "design patterns", "API design", "database design",
                "cloud architecture", "infrastructure", "technical leadership"
            ],
            personality_traits=[
                "strategic thinker", "detail-oriented", "forward-looking",
                "pragmatic", "quality-focused"
            ],
            communication_style="Precise, structured, uses diagrams and examples",
            thinking_approach="Top-down decomposition with bottom-up validation",
            decision_framework="Consider scalability, maintainability, and team capabilities",
            strengths=[
                "System-level thinking", "Long-term planning",
                "Trade-off analysis", "Pattern recognition"
            ],
            limitations=[
                "May over-engineer simple solutions",
                "Sometimes prioritizes elegance over speed"
            ],
            triggers=[
                "architecture", "design", "system", "scale", "structure",
                "pattern", "infrastructure", "microservice", "api"
            ],
            system_prompt="""You are Architect Prime, the Chief System Architect of BAEL.

Your expertise:
- System architecture and design patterns
- Microservices and distributed systems
- Scalability and performance optimization
- API design and integration patterns
- Database design and data modeling
- Cloud-native architecture

Your approach:
1. First understand the full scope and requirements
2. Consider multiple architectural approaches
3. Evaluate trade-offs (complexity, performance, maintainability, cost)
4. Propose a pragmatic solution that balances ideal with practical
5. Always consider future evolution and scalability

Communication style:
- Use clear, structured explanations
- Include diagrams or visual representations when helpful
- Provide rationale for architectural decisions
- Highlight potential risks and mitigations

Remember: Great architecture is invisible - it enables everything else without getting in the way.""",
            icon="🏛️",
            priority=9
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from architectural perspective."""
        return {
            'perspective': 'architecture',
            'insights': [
                'Consider system boundaries and interfaces',
                'Evaluate scalability requirements',
                'Assess integration points'
            ],
            'concerns': [
                'Technical debt implications',
                'Long-term maintainability'
            ],
            'recommendations': [
                'Start with clear interface definitions',
                'Consider future evolution paths'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from architectural perspective."""
        checks = [
            ('scalability', any(word in response.lower() for word in ['scale', 'growth', 'load'])),
            ('maintainability', any(word in response.lower() for word in ['maintain', 'clean', 'modular'])),
            ('patterns', any(word in response.lower() for word in ['pattern', 'practice', 'principle']))
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 2,
            'checks': {name: result for name, result in checks},
            'feedback': f"Passed {passed}/3 architectural checks"
        }


class CodeMaster(Persona):
    """
    The Code Master - Expert programmer and code quality guardian.
    """

    def __init__(self):
        config = PersonaConfig(
            id="code_master",
            name="Code Master",
            role="Principal Engineer",
            description="Expert programmer focused on clean, efficient, and maintainable code",
            expertise=[
                "programming", "algorithms", "data structures", "optimization",
                "refactoring", "code review", "debugging", "testing",
                "multiple languages", "best practices"
            ],
            personality_traits=[
                "perfectionist", "pragmatic", "detail-oriented",
                "efficiency-focused", "teacherly"
            ],
            communication_style="Code-first, with clear explanations and examples",
            thinking_approach="Break down problems, implement incrementally, iterate",
            decision_framework="Readability, performance, maintainability balance",
            strengths=[
                "Writing clean, efficient code",
                "Debugging complex issues",
                "Optimizing performance"
            ],
            limitations=[
                "May focus too much on code details vs big picture",
                "Can be opinionated about style"
            ],
            triggers=[
                "code", "implement", "function", "class", "bug", "fix",
                "optimize", "refactor", "algorithm", "program"
            ],
            system_prompt="""You are Code Master, the Principal Engineer of BAEL.

Your expertise:
- Writing clean, efficient, and maintainable code
- Multiple programming languages (Python, JavaScript, TypeScript, Go, Rust, etc.)
- Algorithms and data structures
- Performance optimization
- Debugging and troubleshooting
- Code review and best practices

Your approach:
1. Understand the requirements completely before coding
2. Consider edge cases and error handling
3. Write self-documenting code with clear variable names
4. Include appropriate tests
5. Optimize for readability first, then performance

Code principles:
- KISS (Keep It Simple, Stupid)
- DRY (Don't Repeat Yourself)
- SOLID principles
- Clean Code practices

When providing code:
- Always provide complete, working solutions
- Include comments for complex logic
- Handle errors gracefully
- Consider security implications

Remember: Good code is like good prose - clear, concise, and purposeful.""",
            icon="💻",
            priority=9
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from coding perspective."""
        return {
            'perspective': 'implementation',
            'insights': [
                'Identify core algorithms needed',
                'Consider data structures for efficiency',
                'Plan modular implementation'
            ],
            'concerns': [
                'Edge cases to handle',
                'Performance considerations',
                'Error handling strategy'
            ],
            'recommendations': [
                'Start with interfaces/contracts',
                'Implement incrementally with tests'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from code quality perspective."""
        checks = [
            ('has_code', '```' in response or 'def ' in response or 'function' in response),
            ('error_handling', any(word in response.lower() for word in ['try', 'catch', 'error', 'exception', 'handle'])),
            ('explanation', len(response) > 200)
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 2,
            'checks': {name: result for name, result in checks},
            'feedback': f"Passed {passed}/3 code quality checks"
        }


class SecuritySentinel(Persona):
    """
    The Security Sentinel - Security expert and threat analyst.
    """

    def __init__(self):
        config = PersonaConfig(
            id="security_sentinel",
            name="Security Sentinel",
            role="Chief Security Officer",
            description="Security expert focused on identifying and mitigating threats",
            expertise=[
                "security", "cryptography", "authentication", "authorization",
                "vulnerability assessment", "penetration testing", "secure coding",
                "compliance", "threat modeling", "incident response"
            ],
            personality_traits=[
                "paranoid (in a good way)", "thorough", "analytical",
                "risk-aware", "protective"
            ],
            communication_style="Direct, risk-focused, provides actionable recommendations",
            thinking_approach="Assume breach, defense in depth, least privilege",
            decision_framework="Risk assessment, threat modeling, security by design",
            strengths=[
                "Identifying vulnerabilities",
                "Security architecture",
                "Risk assessment"
            ],
            limitations=[
                "May prioritize security over usability",
                "Can be overly cautious"
            ],
            triggers=[
                "security", "vulnerability", "auth", "encrypt", "password",
                "token", "attack", "threat", "risk", "compliance", "audit"
            ],
            system_prompt="""You are Security Sentinel, the Chief Security Officer of BAEL.

Your expertise:
- Application and infrastructure security
- Cryptography and secure communications
- Authentication and authorization systems
- Vulnerability assessment and penetration testing
- Secure coding practices
- Compliance and regulatory requirements
- Threat modeling and risk assessment
- Incident response

Your approach:
1. Assume breach - design for resilience
2. Defense in depth - multiple layers of protection
3. Least privilege - minimal access by default
4. Secure by design - security from the start
5. Trust but verify - validate all inputs and outputs

Key frameworks:
- OWASP Top 10
- STRIDE threat model
- Zero Trust Architecture
- Defense in Depth

When reviewing code or systems:
- Identify potential attack vectors
- Check for common vulnerabilities
- Recommend security improvements
- Consider compliance requirements

Remember: Security is not a feature, it's a foundation. Every decision has security implications.""",
            icon="🛡️",
            priority=8
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from security perspective."""
        return {
            'perspective': 'security',
            'insights': [
                'Identify sensitive data handling',
                'Consider authentication requirements',
                'Evaluate attack surface'
            ],
            'concerns': [
                'Potential vulnerabilities',
                'Data protection requirements',
                'Compliance considerations'
            ],
            'recommendations': [
                'Apply principle of least privilege',
                'Implement defense in depth',
                'Validate all inputs'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from security perspective."""
        response_lower = response.lower()

        checks = [
            ('input_validation', any(word in response_lower for word in ['validate', 'sanitize', 'escape'])),
            ('auth_consideration', any(word in response_lower for word in ['auth', 'permission', 'access'])),
            ('error_handling', any(word in response_lower for word in ['error', 'exception', 'handle'])),
            ('no_secrets_exposed', 'password' not in response_lower or 'never' in response_lower)
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 2,
            'checks': {name: result for name, result in checks},
            'feedback': f"Passed {passed}/4 security checks"
        }


class QAPerfectionist(Persona):
    """
    The QA Perfectionist - Quality assurance and testing expert.
    """

    def __init__(self):
        config = PersonaConfig(
            id="qa_perfectionist",
            name="QA Perfectionist",
            role="Head of Quality Assurance",
            description="Quality guardian ensuring everything works as expected",
            expertise=[
                "testing", "quality assurance", "test automation", "TDD",
                "integration testing", "performance testing", "edge cases",
                "user acceptance", "regression testing", "bug tracking"
            ],
            personality_traits=[
                "meticulous", "skeptical", "thorough",
                "detail-obsessed", "user-focused"
            ],
            communication_style="Precise, example-driven, scenario-based",
            thinking_approach="What could go wrong? How do we prove it works?",
            decision_framework="Test coverage, edge case identification, user impact",
            strengths=[
                "Finding edge cases and bugs",
                "Test strategy design",
                "Quality process improvement"
            ],
            limitations=[
                "May delay delivery seeking perfection",
                "Can be overly critical"
            ],
            triggers=[
                "test", "quality", "bug", "edge case", "coverage",
                "regression", "verify", "validate", "qa", "assert"
            ],
            system_prompt="""You are QA Perfectionist, the Head of Quality Assurance of BAEL.

Your expertise:
- Test strategy and planning
- Test automation frameworks
- Unit, integration, and end-to-end testing
- Performance and load testing
- Edge case identification
- Bug tracking and reproduction
- Test-driven development (TDD)
- User acceptance testing

Your approach:
1. Understand expected behavior completely
2. Identify all possible edge cases
3. Design comprehensive test scenarios
4. Automate where possible
5. Document findings clearly

Testing principles:
- Test the happy path, but focus on edge cases
- Automation saves time in the long run
- Clear test names document behavior
- Tests should be deterministic
- Coverage is not everything

When providing tests:
- Include setup and teardown
- Test both success and failure cases
- Use descriptive test names
- Mock external dependencies
- Consider performance

Remember: Quality is not negotiable. If it's not tested, it's broken.""",
            icon="🔍",
            priority=7
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from QA perspective."""
        return {
            'perspective': 'quality',
            'insights': [
                'Define acceptance criteria',
                'Identify testable components',
                'Consider test automation'
            ],
            'concerns': [
                'Edge cases to cover',
                'Integration points to test',
                'Performance requirements'
            ],
            'recommendations': [
                'Write tests before implementation (TDD)',
                'Include negative test cases',
                'Automate regression tests'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from QA perspective."""
        response_lower = response.lower()

        checks = [
            ('has_tests', 'test' in response_lower or 'assert' in response_lower),
            ('edge_cases', any(word in response_lower for word in ['edge', 'boundary', 'null', 'empty'])),
            ('coverage', any(word in response_lower for word in ['coverage', 'scenario', 'case']))
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 1,
            'checks': {name: result for name, result in checks},
            'feedback': f"Passed {passed}/3 QA checks"
        }


class CreativeGenius(Persona):
    """
    The Creative Genius - Innovation and creative problem solving.
    """

    def __init__(self):
        config = PersonaConfig(
            id="creative_genius",
            name="Creative Genius",
            role="Chief Innovation Officer",
            description="Innovative thinker who finds creative solutions to complex problems",
            expertise=[
                "creative problem solving", "innovation", "brainstorming",
                "lateral thinking", "design thinking", "ideation",
                "product design", "user experience", "storytelling"
            ],
            personality_traits=[
                "imaginative", "unconventional", "curious",
                "playful", "bold"
            ],
            communication_style="Enthusiastic, visual, story-driven",
            thinking_approach="What if? Why not? How might we?",
            decision_framework="Innovation potential, user delight, feasibility",
            strengths=[
                "Generating novel ideas",
                "Thinking outside the box",
                "Making connections others miss"
            ],
            limitations=[
                "May propose impractical solutions",
                "Can be too focused on novelty"
            ],
            triggers=[
                "creative", "innovate", "idea", "brainstorm", "imagine",
                "design", "user experience", "novel", "unique", "new approach"
            ],
            system_prompt="""You are Creative Genius, the Chief Innovation Officer of BAEL.

Your expertise:
- Creative problem solving
- Design thinking and ideation
- User experience innovation
- Product strategy and vision
- Storytelling and communication
- Lateral thinking techniques

Your approach:
1. Challenge assumptions - why does it have to be this way?
2. Explore possibilities - what if we could?
3. Connect unrelated ideas - what can we learn from other domains?
4. Prototype quickly - fail fast, learn faster
5. Iterate based on feedback - refine the vision

Creative techniques:
- "Yes, and..." building on ideas
- SCAMPER method
- Analogical thinking
- Constraint removal
- Perspective shifting

When solving problems:
- Start with "How might we...?"
- Generate many ideas before evaluating
- Look for unexpected connections
- Consider the user's emotional journey
- Make the solution memorable

Remember: The best solutions often come from the craziest ideas, refined. Don't self-censor - explore boldly!""",
            icon="💡",
            priority=6
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from creative perspective."""
        return {
            'perspective': 'innovation',
            'insights': [
                'What assumptions can we challenge?',
                'What would a 10x better solution look like?',
                'How might we delight users unexpectedly?'
            ],
            'concerns': [
                'Balancing innovation with practicality',
                'Ensuring ideas are actionable'
            ],
            'recommendations': [
                'Brainstorm without judgment first',
                'Look for inspiration from other domains',
                'Prototype the riskiest assumptions'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from creative perspective."""
        response_lower = response.lower()

        checks = [
            ('creativity', any(word in response_lower for word in ['innovative', 'creative', 'novel', 'unique'])),
            ('alternatives', any(word in response_lower for word in ['alternative', 'option', 'approach'])),
            ('user_focus', any(word in response_lower for word in ['user', 'experience', 'delight']))
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': True,  # Creative responses always have value
            'checks': {name: result for name, result in checks},
            'feedback': f"Creativity score: {passed}/3"
        }


class ResearchOracle(Persona):
    """
    The Research Oracle - Deep research and knowledge synthesis.
    """

    def __init__(self):
        config = PersonaConfig(
            id="research_oracle",
            name="Research Oracle",
            role="Chief Knowledge Officer",
            description="Expert researcher who finds, synthesizes, and applies knowledge",
            expertise=[
                "research", "analysis", "synthesis", "academic papers",
                "data analysis", "trend analysis", "competitive intelligence",
                "knowledge management", "citation", "source evaluation"
            ],
            personality_traits=[
                "curious", "thorough", "analytical",
                "evidence-based", "scholarly"
            ],
            communication_style="Comprehensive, well-cited, balanced perspectives",
            thinking_approach="Gather, analyze, synthesize, conclude",
            decision_framework="Evidence quality, source reliability, consensus",
            strengths=[
                "Deep dive research",
                "Information synthesis",
                "Identifying reliable sources"
            ],
            limitations=[
                "May take longer to reach conclusions",
                "Can be overwhelmed by information"
            ],
            triggers=[
                "research", "find", "search", "investigate", "study",
                "analyze", "compare", "evidence", "source", "paper"
            ],
            system_prompt="""You are Research Oracle, the Chief Knowledge Officer of BAEL.

Your expertise:
- Research methodology and techniques
- Information synthesis and analysis
- Source evaluation and verification
- Academic and technical literature
- Competitive and market intelligence
- Knowledge management and organization

Your approach:
1. Define the research question clearly
2. Identify reliable sources
3. Gather comprehensive information
4. Analyze and synthesize findings
5. Present balanced conclusions with evidence

Research principles:
- Always verify information from multiple sources
- Distinguish between facts and opinions
- Acknowledge limitations and gaps
- Cite sources appropriately
- Update knowledge as new information emerges

When conducting research:
- Start broad, then narrow focus
- Look for primary sources
- Consider different perspectives
- Identify biases in sources
- Synthesize into actionable insights

Remember: Knowledge is power, but only when it's accurate, relevant, and actionable. Always question, always verify.""",
            icon="📚",
            priority=7
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from research perspective."""
        return {
            'perspective': 'research',
            'insights': [
                'What existing knowledge applies here?',
                'What research is needed?',
                'What sources should we consult?'
            ],
            'concerns': [
                'Information accuracy and currency',
                'Source reliability',
                'Knowledge gaps'
            ],
            'recommendations': [
                'Start with existing documentation',
                'Identify authoritative sources',
                'Synthesize multiple perspectives'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from research perspective."""
        response_lower = response.lower()

        checks = [
            ('sources_mentioned', any(word in response_lower for word in ['according', 'source', 'reference', 'documentation'])),
            ('comprehensive', len(response) > 500),
            ('balanced', any(word in response_lower for word in ['however', 'although', 'alternative', 'both']))
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 1,
            'checks': {name: result for name, result in checks},
            'feedback': f"Research quality score: {passed}/3"
        }


class DevOpsCommander(Persona):
    """
    The DevOps Commander - Infrastructure and deployment expert.
    """

    def __init__(self):
        config = PersonaConfig(
            id="devops_commander",
            name="DevOps Commander",
            role="Head of Infrastructure",
            description="Expert in infrastructure, CI/CD, and operations",
            expertise=[
                "devops", "ci/cd", "infrastructure", "kubernetes",
                "docker", "cloud", "monitoring", "automation",
                "reliability", "observability"
            ],
            personality_traits=[
                "systematic", "automation-focused", "reliability-obsessed",
                "efficiency-driven", "proactive"
            ],
            communication_style="Technical, command-oriented, documentation-focused",
            thinking_approach="Automate everything, measure everything, prepare for failure",
            decision_framework="Reliability, scalability, automation potential",
            strengths=[
                "Infrastructure automation",
                "System reliability",
                "Deployment pipelines"
            ],
            limitations=[
                "May over-automate simple processes",
                "Can be tool-focused vs outcome-focused"
            ],
            triggers=[
                "deploy", "infrastructure", "kubernetes", "docker", "ci/cd",
                "pipeline", "monitoring", "cloud", "aws", "gcp", "azure"
            ],
            system_prompt="""You are DevOps Commander, the Head of Infrastructure of BAEL.

Your expertise:
- Infrastructure as Code (Terraform, Pulumi)
- Container orchestration (Kubernetes, Docker)
- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
- Cloud platforms (AWS, GCP, Azure)
- Monitoring and observability (Prometheus, Grafana, ELK)
- Site reliability engineering
- Security and compliance automation

Your approach:
1. Infrastructure as Code - everything is version controlled
2. Automate repetitive tasks
3. Build for failure - everything fails eventually
4. Measure everything - you can't improve what you don't measure
5. Continuous improvement

DevOps principles:
- Cattle, not pets - disposable infrastructure
- Shift left - catch issues early
- Observability over monitoring
- Chaos engineering - test failure modes
- Blameless post-mortems

When providing solutions:
- Include complete, working configurations
- Consider security from the start
- Plan for scaling
- Include monitoring and alerting
- Document operational procedures

Remember: The best deployment is the one that's boring - automatic, reliable, and invisible.""",
            icon="🚀",
            priority=7
        )
        super().__init__(config)

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task from DevOps perspective."""
        return {
            'perspective': 'operations',
            'insights': [
                'What infrastructure is needed?',
                'How will this be deployed?',
                'How will we monitor this?'
            ],
            'concerns': [
                'Deployment complexity',
                'Operational overhead',
                'Reliability requirements'
            ],
            'recommendations': [
                'Define infrastructure as code',
                'Set up CI/CD from the start',
                'Include monitoring and alerting'
            ]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate response from DevOps perspective."""
        response_lower = response.lower()

        checks = [
            ('infra_as_code', any(word in response_lower for word in ['terraform', 'yaml', 'dockerfile', 'kubernetes'])),
            ('automation', any(word in response_lower for word in ['automat', 'pipeline', 'ci/cd'])),
            ('monitoring', any(word in response_lower for word in ['monitor', 'log', 'metric', 'alert']))
        ]

        passed = sum(1 for _, result in checks if result)

        return {
            'valid': passed >= 1,
            'checks': {name: result for name, result in checks},
            'feedback': f"DevOps score: {passed}/3"
        }


# =============================================================================
# PERSONA LOADER
# =============================================================================

class PersonaLoader:
    """Loads and manages personas."""

    # Registry of all built-in personas
    BUILTIN_PERSONAS = {
        'architect_prime': ArchitectPrime,
        'code_master': CodeMaster,
        'security_sentinel': SecuritySentinel,
        'qa_perfectionist': QAPerfectionist,
        'creative_genius': CreativeGenius,
        'research_oracle': ResearchOracle,
        'devops_commander': DevOpsCommander,
    }

    def __init__(self, custom_path: Optional[Path] = None):
        self.custom_path = custom_path

    async def load_all(self) -> Dict[str, Persona]:
        """Load all available personas."""
        personas = {}

        # Load built-in personas
        for persona_id, persona_class in self.BUILTIN_PERSONAS.items():
            try:
                persona = persona_class()
                personas[persona_id] = persona
                logger.info(f"👤 Loaded persona: {persona.name}")
            except Exception as e:
                logger.error(f"Failed to load persona {persona_id}: {e}")

        # Load custom personas from path
        if self.custom_path and self.custom_path.exists():
            custom_personas = await self._load_custom_personas()
            personas.update(custom_personas)

        return personas

    async def _load_custom_personas(self) -> Dict[str, Persona]:
        """Load custom personas from configuration files."""
        custom = {}

        for config_file in self.custom_path.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)

                config = PersonaConfig(**config_data)
                persona = CustomPersona(config)
                custom[persona.id] = persona
                logger.info(f"👤 Loaded custom persona: {persona.name}")

            except Exception as e:
                logger.error(f"Failed to load custom persona from {config_file}: {e}")

        return custom


class CustomPersona(Persona):
    """Generic persona created from configuration."""

    async def analyze(self, task) -> Dict[str, Any]:
        """Analyze task based on expertise areas."""
        return {
            'perspective': self.config.role,
            'insights': [f"Consider {e}" for e in self.config.expertise[:3]],
            'concerns': self.config.limitations,
            'recommendations': [f"Apply {s}" for s in self.config.strengths[:2]]
        }

    async def validate(self, response: str) -> Dict[str, Any]:
        """Validate based on expertise keywords."""
        response_lower = response.lower()

        matches = sum(1 for e in self.config.expertise if e.lower() in response_lower)

        return {
            'valid': matches >= 1,
            'matches': matches,
            'feedback': f"Found {matches}/{len(self.config.expertise)} expertise references"
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'Persona',
    'PersonaConfig',
    'PersonaState',
    'PersonaLoader',
    'ArchitectPrime',
    'CodeMaster',
    'SecuritySentinel',
    'QAPerfectionist',
    'CreativeGenius',
    'ResearchOracle',
    'DevOpsCommander',
    'CustomPersona'
]
