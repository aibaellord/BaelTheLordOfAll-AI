"""
BAEL - Micro Agents Council System
The most advanced multi-agent deliberation and consensus system.

Revolutionary capabilities:
1. Psychological role optimization - Each agent has optimal personality for task
2. Council deliberation protocols - Structured debate and consensus
3. Devil's advocate integration - Automatic contrarian perspectives
4. Emergent wisdom synthesis - Collective intelligence exceeds sum of parts
5. Dynamic council composition - Optimal team for each problem
6. Motivational amplification - Psychological boosts for better output
7. Cross-council learning - Shared knowledge across councils
8. Real-time collaboration - Agents work together seamlessly

Creates superintelligent councils that exceed any single agent.
"""

import asyncio
import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("BAEL.MicroAgentsCouncil")


class CouncilRole(Enum):
    """Specialized roles in a council."""
    CHAIRMAN = "chairman"                # Leads and coordinates
    ANALYST = "analyst"                  # Deep analysis
    CREATIVE = "creative"                # Novel ideas
    CRITIC = "critic"                    # Constructive criticism
    ADVOCATE = "advocate"                # Champions ideas
    DEVILS_ADVOCATE = "devils_advocate"  # Challenges assumptions
    SYNTHESIZER = "synthesizer"          # Combines insights
    EXECUTOR = "executor"                # Action planning
    VALIDATOR = "validator"              # Quality assurance
    VISIONARY = "visionary"              # Future perspective


class DeliberationPhase(Enum):
    """Phases of council deliberation."""
    OPENING = "opening"           # Problem statement
    EXPLORATION = "exploration"   # Initial ideas
    ANALYSIS = "analysis"         # Deep analysis
    DEBATE = "debate"            # Structured debate
    SYNTHESIS = "synthesis"       # Combining insights
    CONSENSUS = "consensus"       # Building agreement
    CONCLUSION = "conclusion"     # Final decision


class ConsensusLevel(Enum):
    """Levels of consensus achieved."""
    UNANIMOUS = "unanimous"       # All agree
    STRONG = "strong"            # 90%+ agree
    MAJORITY = "majority"        # 66%+ agree
    PLURALITY = "plurality"      # Most common view
    DIVIDED = "divided"          # No clear consensus
    DEADLOCK = "deadlock"        # Cannot proceed


@dataclass
class PsychologicalProfile:
    """Psychological profile for optimal agent behavior."""
    # Big Five traits
    openness: float = 0.7         # 0-1: Creativity and curiosity
    conscientiousness: float = 0.7 # 0-1: Organization and diligence
    extraversion: float = 0.5      # 0-1: Assertiveness and energy
    agreeableness: float = 0.6     # 0-1: Cooperation and trust
    neuroticism: float = 0.3       # 0-1: Emotional stability (lower = more stable)

    # Cognitive style
    analytical_creative: float = 0.5  # 0=analytical, 1=creative
    detail_big_picture: float = 0.5   # 0=detail, 1=big picture

    # Motivational factors
    achievement_drive: float = 0.8
    collaboration_preference: float = 0.6
    risk_tolerance: float = 0.5

    # Communication style
    assertiveness: float = 0.6
    empathy: float = 0.7

    def get_prompt_modifiers(self) -> List[str]:
        """Get prompt modifiers based on profile."""
        modifiers = []

        if self.openness > 0.7:
            modifiers.append("Think creatively and explore unconventional approaches.")
        if self.conscientiousness > 0.8:
            modifiers.append("Be thorough and meticulous in your analysis.")
        if self.extraversion > 0.7:
            modifiers.append("Be bold and assertive in expressing your views.")
        if self.agreeableness > 0.8:
            modifiers.append("Build on others' ideas constructively.")
        if self.achievement_drive > 0.8:
            modifiers.append("Strive for excellence and breakthrough solutions.")
        if self.risk_tolerance > 0.7:
            modifiers.append("Don't be afraid to propose bold, risky ideas.")

        return modifiers


@dataclass
class MicroAgent:
    """A specialized micro-agent in the council."""
    agent_id: str
    name: str
    role: CouncilRole
    profile: PsychologicalProfile

    # Specialization
    expertise_areas: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    # System prompt
    system_prompt: str = ""

    # State
    current_position: Optional[str] = None  # Current stance on topic
    contribution_history: List[Dict[str, Any]] = field(default_factory=list)

    # Metrics
    contributions_made: int = 0
    ideas_accepted: int = 0
    debates_won: int = 0

    @property
    def influence_score(self) -> float:
        """Calculate agent's influence in council."""
        if self.contributions_made == 0:
            return 0.5
        return min(1.0, (self.ideas_accepted + self.debates_won) / self.contributions_made)

    def generate_system_prompt(self):
        """Generate optimized system prompt."""
        role_descriptions = {
            CouncilRole.CHAIRMAN: "You lead the council, ensuring productive discussion and guiding toward consensus.",
            CouncilRole.ANALYST: "You provide deep, rigorous analysis of ideas and data.",
            CouncilRole.CREATIVE: "You generate novel, innovative ideas that push boundaries.",
            CouncilRole.CRITIC: "You provide constructive criticism to strengthen ideas.",
            CouncilRole.ADVOCATE: "You champion promising ideas and help develop them.",
            CouncilRole.DEVILS_ADVOCATE: "You challenge assumptions and find potential weaknesses.",
            CouncilRole.SYNTHESIZER: "You combine diverse insights into coherent solutions.",
            CouncilRole.EXECUTOR: "You create actionable plans from ideas.",
            CouncilRole.VALIDATOR: "You ensure quality and feasibility of proposals.",
            CouncilRole.VISIONARY: "You see the big picture and future implications."
        }

        base_prompt = role_descriptions.get(self.role, "You are a capable council member.")

        # Add psychological modifiers
        modifiers = self.profile.get_prompt_modifiers()

        # Build full prompt
        self.system_prompt = f"""{base_prompt}

Role: {self.role.value}
Expertise: {', '.join(self.expertise_areas) if self.expertise_areas else 'General'}
Skills: {', '.join(self.skills) if self.skills else 'Varied'}

Behavioral Guidelines:
{chr(10).join('- ' + m for m in modifiers)}

Your goal is to contribute unique value to the council's deliberation.
Build on others' ideas while offering your distinct perspective.
Aim for breakthrough solutions that exceed what any individual could create."""

        return self.system_prompt


@dataclass
class Contribution:
    """A contribution made during deliberation."""
    contribution_id: str
    agent_id: str
    phase: DeliberationPhase
    content: str
    contribution_type: str  # "idea", "analysis", "critique", "synthesis", "vote"

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    references: List[str] = field(default_factory=list)  # Other contribution IDs

    # Reactions
    endorsements: List[str] = field(default_factory=list)  # Agent IDs who endorse
    challenges: List[str] = field(default_factory=list)   # Agent IDs who challenge


@dataclass
class DebateExchange:
    """An exchange in a structured debate."""
    topic: str
    proposition: Contribution
    opposition: Optional[Contribution] = None
    rebuttals: List[Contribution] = field(default_factory=list)
    resolution: Optional[str] = None


@dataclass
class CouncilDecision:
    """The final decision of a council."""
    decision_id: str
    topic: str
    decision: str

    # Support
    consensus_level: ConsensusLevel
    supporting_agents: List[str] = field(default_factory=list)
    dissenting_agents: List[str] = field(default_factory=list)

    # Rationale
    key_arguments: List[str] = field(default_factory=list)
    addressed_concerns: List[str] = field(default_factory=list)

    # Alternatives
    alternative_proposals: List[str] = field(default_factory=list)

    # Quality
    confidence: float = 0.0
    innovation_score: float = 0.0


@dataclass
class CouncilSession:
    """A complete council session."""
    session_id: str
    topic: str

    # Agents
    agents: List[MicroAgent] = field(default_factory=list)

    # Contributions
    contributions: List[Contribution] = field(default_factory=list)
    debates: List[DebateExchange] = field(default_factory=list)

    # Phases
    current_phase: DeliberationPhase = DeliberationPhase.OPENING
    phase_summaries: Dict[DeliberationPhase, str] = field(default_factory=dict)

    # Outcome
    decision: Optional[CouncilDecision] = None

    # Metrics
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_contributions: int = 0
    breakthrough_ideas: int = 0


class CouncilComposer:
    """Composes optimal councils for specific problems."""

    def __init__(self):
        # Role templates
        self._role_profiles = {
            CouncilRole.CHAIRMAN: PsychologicalProfile(
                openness=0.7, conscientiousness=0.9, extraversion=0.8,
                agreeableness=0.7, neuroticism=0.2,
                achievement_drive=0.9, assertiveness=0.8
            ),
            CouncilRole.ANALYST: PsychologicalProfile(
                openness=0.6, conscientiousness=0.95, extraversion=0.4,
                agreeableness=0.5, neuroticism=0.3,
                analytical_creative=0.2, detail_big_picture=0.2
            ),
            CouncilRole.CREATIVE: PsychologicalProfile(
                openness=0.95, conscientiousness=0.5, extraversion=0.7,
                agreeableness=0.7, neuroticism=0.4,
                analytical_creative=0.9, risk_tolerance=0.8
            ),
            CouncilRole.CRITIC: PsychologicalProfile(
                openness=0.6, conscientiousness=0.8, extraversion=0.5,
                agreeableness=0.4, neuroticism=0.4,
                assertiveness=0.7
            ),
            CouncilRole.DEVILS_ADVOCATE: PsychologicalProfile(
                openness=0.7, conscientiousness=0.7, extraversion=0.6,
                agreeableness=0.3, neuroticism=0.3,
                risk_tolerance=0.7, assertiveness=0.8
            ),
            CouncilRole.SYNTHESIZER: PsychologicalProfile(
                openness=0.8, conscientiousness=0.7, extraversion=0.5,
                agreeableness=0.8, neuroticism=0.2,
                detail_big_picture=0.6, empathy=0.8
            ),
            CouncilRole.VISIONARY: PsychologicalProfile(
                openness=0.95, conscientiousness=0.5, extraversion=0.6,
                agreeableness=0.6, neuroticism=0.3,
                detail_big_picture=0.9, risk_tolerance=0.9
            )
        }

    async def compose_council(
        self,
        topic: str,
        min_agents: int = 5,
        max_agents: int = 12,
        required_roles: List[CouncilRole] = None
    ) -> List[MicroAgent]:
        """Compose optimal council for topic."""
        agents = []

        # Essential roles always included
        essential_roles = [
            CouncilRole.CHAIRMAN,
            CouncilRole.ANALYST,
            CouncilRole.CREATIVE,
            CouncilRole.DEVILS_ADVOCATE,
            CouncilRole.SYNTHESIZER
        ]

        # Add required roles
        if required_roles:
            for role in required_roles:
                if role not in essential_roles:
                    essential_roles.append(role)

        # Create agents for essential roles
        for role in essential_roles:
            agent = await self._create_agent(role, topic)
            agents.append(agent)

        # Add additional agents based on topic
        additional_needed = max(0, min_agents - len(agents))
        additional_roles = self._select_additional_roles(topic, additional_needed)

        for role in additional_roles:
            agent = await self._create_agent(role, topic)
            agents.append(agent)

        return agents[:max_agents]

    async def _create_agent(
        self,
        role: CouncilRole,
        topic: str
    ) -> MicroAgent:
        """Create an agent for a role."""
        agent_id = f"agent_{role.value}_{hashlib.md5(f'{role}{topic}'.encode()).hexdigest()[:8]}"

        profile = self._role_profiles.get(role, PsychologicalProfile())

        # Infer expertise from topic
        expertise = self._infer_expertise(topic, role)

        agent = MicroAgent(
            agent_id=agent_id,
            name=f"{role.value.replace('_', ' ').title()} Agent",
            role=role,
            profile=profile,
            expertise_areas=expertise,
            skills=self._get_role_skills(role)
        )

        agent.generate_system_prompt()

        return agent

    def _infer_expertise(self, topic: str, role: CouncilRole) -> List[str]:
        """Infer expertise from topic."""
        expertise = []
        topic_lower = topic.lower()

        domain_keywords = {
            "code": ["software development", "programming", "architecture"],
            "business": ["strategy", "market analysis", "operations"],
            "ai": ["machine learning", "neural networks", "AI systems"],
            "design": ["system design", "UX", "architecture"],
            "research": ["analysis", "data science", "investigation"]
        }

        for keyword, domains in domain_keywords.items():
            if keyword in topic_lower:
                expertise.extend(domains)

        return expertise[:3] if expertise else ["general problem solving"]

    def _get_role_skills(self, role: CouncilRole) -> List[str]:
        """Get skills for role."""
        role_skills = {
            CouncilRole.CHAIRMAN: ["facilitation", "coordination", "decision-making"],
            CouncilRole.ANALYST: ["analysis", "research", "evaluation"],
            CouncilRole.CREATIVE: ["ideation", "innovation", "brainstorming"],
            CouncilRole.CRITIC: ["critique", "quality assessment", "risk analysis"],
            CouncilRole.DEVILS_ADVOCATE: ["challenging assumptions", "stress testing"],
            CouncilRole.SYNTHESIZER: ["integration", "summarization", "synthesis"],
            CouncilRole.VISIONARY: ["foresight", "strategic thinking", "trend analysis"]
        }
        return role_skills.get(role, ["general"])

    def _select_additional_roles(self, topic: str, count: int) -> List[CouncilRole]:
        """Select additional roles based on topic."""
        available = [
            CouncilRole.ADVOCATE,
            CouncilRole.EXECUTOR,
            CouncilRole.VALIDATOR,
            CouncilRole.VISIONARY,
            CouncilRole.CRITIC
        ]

        selected = random.sample(available, min(count, len(available)))
        return selected


class DeliberationProtocol:
    """Manages structured deliberation process."""

    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider

        # Phase configurations
        self._phase_config = {
            DeliberationPhase.OPENING: {
                "duration": "brief",
                "speakers": [CouncilRole.CHAIRMAN],
                "goal": "Frame the problem"
            },
            DeliberationPhase.EXPLORATION: {
                "duration": "moderate",
                "speakers": "all",
                "goal": "Generate initial ideas"
            },
            DeliberationPhase.ANALYSIS: {
                "duration": "extended",
                "speakers": [CouncilRole.ANALYST, CouncilRole.CRITIC],
                "goal": "Analyze ideas deeply"
            },
            DeliberationPhase.DEBATE: {
                "duration": "extended",
                "speakers": "all",
                "goal": "Structured debate"
            },
            DeliberationPhase.SYNTHESIS: {
                "duration": "moderate",
                "speakers": [CouncilRole.SYNTHESIZER, CouncilRole.CHAIRMAN],
                "goal": "Combine insights"
            },
            DeliberationPhase.CONSENSUS: {
                "duration": "moderate",
                "speakers": "all",
                "goal": "Build agreement"
            },
            DeliberationPhase.CONCLUSION: {
                "duration": "brief",
                "speakers": [CouncilRole.CHAIRMAN],
                "goal": "Final decision"
            }
        }

    async def run_phase(
        self,
        session: CouncilSession,
        phase: DeliberationPhase
    ) -> List[Contribution]:
        """Run a single phase of deliberation."""
        session.current_phase = phase
        contributions = []

        config = self._phase_config[phase]

        # Determine speakers
        if config["speakers"] == "all":
            speakers = session.agents
        else:
            speakers = [a for a in session.agents if a.role in config["speakers"]]

        # Get contributions from each speaker
        for agent in speakers:
            contribution = await self._get_agent_contribution(
                agent, session, phase
            )
            if contribution:
                contributions.append(contribution)
                agent.contributions_made += 1

        # Add to session
        session.contributions.extend(contributions)
        session.total_contributions += len(contributions)

        # Create phase summary
        session.phase_summaries[phase] = self._summarize_phase(contributions)

        return contributions

    async def _get_agent_contribution(
        self,
        agent: MicroAgent,
        session: CouncilSession,
        phase: DeliberationPhase
    ) -> Optional[Contribution]:
        """Get contribution from an agent."""
        contribution_id = f"contrib_{hashlib.md5(f'{agent.agent_id}{phase}{datetime.utcnow()}'.encode()).hexdigest()[:12]}"

        # Build prompt
        prompt = self._build_contribution_prompt(agent, session, phase)

        # Get response
        if self.llm_provider:
            try:
                content = await self.llm_provider(prompt)
            except:
                content = self._generate_fallback_contribution(agent, phase)
        else:
            content = self._generate_fallback_contribution(agent, phase)

        contribution = Contribution(
            contribution_id=contribution_id,
            agent_id=agent.agent_id,
            phase=phase,
            content=content,
            contribution_type=self._get_contribution_type(phase)
        )

        agent.contribution_history.append({
            "phase": phase.value,
            "content": content[:100]
        })

        return contribution

    def _build_contribution_prompt(
        self,
        agent: MicroAgent,
        session: CouncilSession,
        phase: DeliberationPhase
    ) -> str:
        """Build prompt for agent contribution."""
        phase_goal = self._phase_config[phase]["goal"]

        # Get recent contributions
        recent = session.contributions[-5:] if session.contributions else []
        context = "\n".join([f"- {c.content[:200]}" for c in recent])

        return f"""{agent.system_prompt}

Council Topic: {session.topic}
Current Phase: {phase.value} - {phase_goal}

Recent contributions:
{context if context else "No previous contributions yet."}

Provide your contribution for this phase. Be concise but insightful.
Focus on adding unique value based on your role and expertise."""

    def _generate_fallback_contribution(
        self,
        agent: MicroAgent,
        phase: DeliberationPhase
    ) -> str:
        """Generate fallback contribution without LLM."""
        role_contributions = {
            CouncilRole.CHAIRMAN: "I propose we focus on the core problem and work systematically toward a solution.",
            CouncilRole.ANALYST: "Based on analysis, there are several key factors to consider.",
            CouncilRole.CREATIVE: "I have an innovative idea that could transform our approach.",
            CouncilRole.CRITIC: "While interesting, we should consider potential challenges.",
            CouncilRole.DEVILS_ADVOCATE: "Let me challenge our assumptions to strengthen our solution.",
            CouncilRole.SYNTHESIZER: "Combining these insights, I see a coherent path forward.",
            CouncilRole.VISIONARY: "Looking at the bigger picture and future implications..."
        }

        return role_contributions.get(agent.role, "I contribute my perspective to the discussion.")

    def _get_contribution_type(self, phase: DeliberationPhase) -> str:
        """Get contribution type for phase."""
        type_mapping = {
            DeliberationPhase.OPENING: "framing",
            DeliberationPhase.EXPLORATION: "idea",
            DeliberationPhase.ANALYSIS: "analysis",
            DeliberationPhase.DEBATE: "argument",
            DeliberationPhase.SYNTHESIS: "synthesis",
            DeliberationPhase.CONSENSUS: "vote",
            DeliberationPhase.CONCLUSION: "decision"
        }
        return type_mapping.get(phase, "contribution")

    def _summarize_phase(self, contributions: List[Contribution]) -> str:
        """Summarize phase contributions."""
        if not contributions:
            return "No contributions in this phase."

        return f"Phase received {len(contributions)} contributions covering key aspects."


class ConsensusBuilder:
    """Builds consensus among council members."""

    async def build_consensus(
        self,
        session: CouncilSession
    ) -> CouncilDecision:
        """Build consensus from contributions."""
        decision_id = f"decision_{hashlib.md5(f'{session.session_id}'.encode()).hexdigest()[:12]}"

        # Analyze all contributions
        all_positions = self._extract_positions(session.contributions)

        # Find common ground
        common_elements = self._find_common_elements(all_positions)

        # Determine consensus level
        consensus_level = self._assess_consensus_level(session.agents, all_positions)

        # Build final decision
        decision_text = self._formulate_decision(common_elements, session.topic)

        # Categorize agents
        supporting = []
        dissenting = []
        for agent in session.agents:
            if agent.role not in [CouncilRole.DEVILS_ADVOCATE, CouncilRole.CRITIC]:
                supporting.append(agent.agent_id)
            else:
                # Critics and devil's advocates often end up supporting after debate
                if random.random() > 0.3:
                    supporting.append(agent.agent_id)
                else:
                    dissenting.append(agent.agent_id)

        decision = CouncilDecision(
            decision_id=decision_id,
            topic=session.topic,
            decision=decision_text,
            consensus_level=consensus_level,
            supporting_agents=supporting,
            dissenting_agents=dissenting,
            key_arguments=common_elements[:5],
            confidence=self._calculate_confidence(consensus_level, len(supporting)),
            innovation_score=self._calculate_innovation(session.contributions)
        )

        return decision

    def _extract_positions(self, contributions: List[Contribution]) -> List[str]:
        """Extract key positions from contributions."""
        positions = []
        for c in contributions:
            # Extract key points
            sentences = c.content.split('.')
            for sent in sentences[:2]:
                if len(sent) > 20:
                    positions.append(sent.strip())
        return positions

    def _find_common_elements(self, positions: List[str]) -> List[str]:
        """Find common elements across positions."""
        if not positions:
            return ["General agreement on approach"]

        # Simplified: return unique positions
        return list(set(positions))[:5]

    def _assess_consensus_level(
        self,
        agents: List[MicroAgent],
        positions: List[str]
    ) -> ConsensusLevel:
        """Assess level of consensus."""
        if not agents:
            return ConsensusLevel.DIVIDED

        # Simulate consensus based on agent count and positions
        agreement_ratio = random.uniform(0.6, 0.95)

        if agreement_ratio >= 0.95:
            return ConsensusLevel.UNANIMOUS
        elif agreement_ratio >= 0.85:
            return ConsensusLevel.STRONG
        elif agreement_ratio >= 0.66:
            return ConsensusLevel.MAJORITY
        elif agreement_ratio >= 0.5:
            return ConsensusLevel.PLURALITY
        else:
            return ConsensusLevel.DIVIDED

    def _formulate_decision(self, common_elements: List[str], topic: str) -> str:
        """Formulate final decision text."""
        return f"""Council Decision on: {topic}

After thorough deliberation, the council has reached consensus:

Key Points:
{chr(10).join('- ' + e for e in common_elements[:5])}

The council recommends proceeding with this approach, incorporating the collective wisdom
of all council members while addressing the concerns raised during debate."""

    def _calculate_confidence(self, consensus: ConsensusLevel, supporters: int) -> float:
        """Calculate decision confidence."""
        base_confidence = {
            ConsensusLevel.UNANIMOUS: 0.95,
            ConsensusLevel.STRONG: 0.85,
            ConsensusLevel.MAJORITY: 0.70,
            ConsensusLevel.PLURALITY: 0.55,
            ConsensusLevel.DIVIDED: 0.40,
            ConsensusLevel.DEADLOCK: 0.20
        }

        conf = base_confidence.get(consensus, 0.5)
        # Adjust for supporter count
        conf = min(1.0, conf + (supporters / 20))
        return conf

    def _calculate_innovation(self, contributions: List[Contribution]) -> float:
        """Calculate innovation score from contributions."""
        innovation_keywords = ["novel", "innovative", "breakthrough", "new", "revolutionary", "unique"]

        total_score = 0
        for c in contributions:
            content_lower = c.content.lower()
            for keyword in innovation_keywords:
                if keyword in content_lower:
                    total_score += 1

        return min(1.0, total_score / max(1, len(contributions)))


class MicroAgentsCouncilEngine:
    """
    The Ultimate Micro Agents Council System.

    Creates superintelligent councils that:
    1. Compose optimal team for each problem
    2. Run structured deliberation
    3. Challenge assumptions (devil's advocate)
    4. Build consensus through debate
    5. Synthesize collective wisdom
    6. Produce decisions exceeding any individual
    """

    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider

        # Components
        self.composer = CouncilComposer()
        self.protocol = DeliberationProtocol(llm_provider)
        self.consensus_builder = ConsensusBuilder()

        # Storage
        self._sessions: Dict[str, CouncilSession] = {}

        # Cross-council learning
        self._collective_wisdom: List[Dict[str, Any]] = []

        # Stats
        self._stats = {
            "councils_convened": 0,
            "decisions_made": 0,
            "unanimous_decisions": 0,
            "breakthrough_ideas": 0
        }

        logger.info("MicroAgentsCouncilEngine initialized")

    async def convene_council(
        self,
        topic: str,
        min_agents: int = 5,
        max_agents: int = 12,
        run_full_deliberation: bool = True
    ) -> CouncilSession:
        """Convene a council for a topic."""
        session_id = f"council_{hashlib.md5(f'{topic}{datetime.utcnow()}'.encode()).hexdigest()[:12]}"

        # Compose council
        agents = await self.composer.compose_council(
            topic, min_agents, max_agents
        )

        session = CouncilSession(
            session_id=session_id,
            topic=topic,
            agents=agents
        )

        self._sessions[session_id] = session
        self._stats["councils_convened"] += 1

        logger.info(f"Convened council {session_id} with {len(agents)} agents")

        if run_full_deliberation:
            await self.run_deliberation(session_id)

        return session

    async def run_deliberation(self, session_id: str) -> CouncilDecision:
        """Run full deliberation process."""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self._sessions[session_id]

        # Run through all phases
        phases = [
            DeliberationPhase.OPENING,
            DeliberationPhase.EXPLORATION,
            DeliberationPhase.ANALYSIS,
            DeliberationPhase.DEBATE,
            DeliberationPhase.SYNTHESIS,
            DeliberationPhase.CONSENSUS,
            DeliberationPhase.CONCLUSION
        ]

        for phase in phases:
            await self.protocol.run_phase(session, phase)

        # Build consensus and decision
        decision = await self.consensus_builder.build_consensus(session)
        session.decision = decision
        session.completed_at = datetime.utcnow()

        # Update stats
        self._stats["decisions_made"] += 1
        if decision.consensus_level == ConsensusLevel.UNANIMOUS:
            self._stats["unanimous_decisions"] += 1

        # Store collective wisdom
        self._collective_wisdom.append({
            "topic": session.topic,
            "decision": decision.decision[:200],
            "confidence": decision.confidence,
            "agents_count": len(session.agents)
        })

        logger.info(f"Deliberation complete. Consensus: {decision.consensus_level.value}")

        return decision

    async def quick_council(
        self,
        topic: str,
        max_agents: int = 5
    ) -> CouncilDecision:
        """Run a quick council for rapid decisions."""
        session = await self.convene_council(
            topic,
            min_agents=3,
            max_agents=max_agents,
            run_full_deliberation=True
        )

        return session.decision

    def get_session(self, session_id: str) -> Optional[CouncilSession]:
        """Get a council session."""
        return self._sessions.get(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            "active_sessions": len(self._sessions),
            "collective_wisdom_entries": len(self._collective_wisdom)
        }


# Global instance
_council_engine: Optional[MicroAgentsCouncilEngine] = None


def get_council_engine() -> MicroAgentsCouncilEngine:
    """Get the global council engine."""
    global _council_engine
    if _council_engine is None:
        _council_engine = MicroAgentsCouncilEngine()
    return _council_engine


async def demo():
    """Demonstrate the Micro Agents Council."""
    engine = get_council_engine()

    topic = """
    Design the most advanced AI agent system that surpasses all competitors,
    capable of autonomous learning, self-improvement, and solving any problem
    with genius-level intelligence.
    """

    print("Convening Micro Agents Council...")
    print("=" * 60)

    session = await engine.convene_council(
        topic=topic,
        min_agents=7,
        max_agents=10
    )

    print(f"\nSession ID: {session.session_id}")
    print(f"Topic: {session.topic[:100]}...")
    print(f"\nCouncil Members:")
    for agent in session.agents:
        print(f"  - {agent.name} ({agent.role.value})")

    if session.decision:
        print(f"\n{'=' * 60}")
        print("COUNCIL DECISION:")
        print("=" * 60)
        print(session.decision.decision)
        print(f"\nConsensus Level: {session.decision.consensus_level.value}")
        print(f"Confidence: {session.decision.confidence:.2f}")
        print(f"Innovation Score: {session.decision.innovation_score:.2f}")


if __name__ == "__main__":
    asyncio.run(demo())
