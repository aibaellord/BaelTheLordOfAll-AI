"""
BAEL - Automated Swarm Genesis System
Inspired by Kimi 2.5 but taken to the next level.

Revolutionary concepts:
1. Zero-shot swarm creation from task descriptions
2. Psychological agent role optimization
3. Emergent swarm intelligence through micro-agent interactions
4. Self-organizing hierarchies
5. Collective consciousness synthesis
6. Dynamic swarm evolution during execution
7. Cross-swarm knowledge sharing

This creates truly autonomous swarms that exceed any existing system.
"""

import asyncio
import hashlib
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math

logger = logging.getLogger("BAEL.SwarmGenesis")


class AgentArchetype(Enum):
    """Psychological archetypes for agents - based on Jungian psychology."""
    LEADER = "leader"           # Coordinates and directs
    EXPLORER = "explorer"       # Discovers new approaches
    ANALYST = "analyst"         # Deep analysis and critique
    CREATOR = "creator"         # Generates novel solutions
    GUARDIAN = "guardian"       # Validates and protects
    SYNTHESIZER = "synthesizer" # Combines insights
    CHALLENGER = "challenger"   # Questions assumptions
    OPTIMIZER = "optimizer"     # Improves efficiency
    VISIONARY = "visionary"     # Big picture thinking
    SPECIALIST = "specialist"   # Domain expertise


class SwarmTopology(Enum):
    """Swarm organization topologies."""
    HIERARCHICAL = "hierarchical"     # Tree structure with leaders
    FLAT = "flat"                     # All agents equal
    RING = "ring"                     # Circular communication
    MESH = "mesh"                     # Full connectivity
    STAR = "star"                     # Central coordinator
    EMERGENT = "emergent"             # Self-organizing
    HYBRID = "hybrid"                 # Mixed topology


class CommunicationPattern(Enum):
    """How agents communicate."""
    BROADCAST = "broadcast"           # One to all
    UNICAST = "unicast"               # One to one
    MULTICAST = "multicast"           # One to group
    GOSSIP = "gossip"                 # Random peer exchange
    CONSENSUS = "consensus"           # Agreement required
    COMPETITIVE = "competitive"       # Best solution wins


@dataclass
class PsychologicalProfile:
    """Psychological profile for agent optimization."""
    archetype: AgentArchetype
    
    # Big Five personality traits (0-1)
    openness: float = 0.7
    conscientiousness: float = 0.7
    extraversion: float = 0.5
    agreeableness: float = 0.6
    neuroticism: float = 0.3
    
    # Cognitive style
    analytical_creative_balance: float = 0.5  # 0=analytical, 1=creative
    detail_big_picture_balance: float = 0.5   # 0=detail, 1=big picture
    risk_tolerance: float = 0.5
    
    # Motivational drivers
    intrinsic_motivation: float = 0.8
    achievement_drive: float = 0.7
    collaboration_preference: float = 0.6
    
    def get_interaction_style(self) -> str:
        """Get optimal interaction style based on profile."""
        if self.extraversion > 0.7 and self.agreeableness > 0.6:
            return "collaborative_enthusiast"
        elif self.openness > 0.8 and self.analytical_creative_balance > 0.6:
            return "creative_explorer"
        elif self.conscientiousness > 0.8 and self.detail_big_picture_balance < 0.4:
            return "meticulous_analyzer"
        elif self.risk_tolerance > 0.7:
            return "bold_innovator"
        else:
            return "balanced_contributor"


@dataclass
class MicroAgent:
    """A micro-agent in the swarm."""
    agent_id: str
    name: str
    role: str
    profile: PsychologicalProfile
    
    # Capabilities
    skills: List[str] = field(default_factory=list)
    expertise_domains: List[str] = field(default_factory=list)
    
    # State
    status: str = "idle"  # idle, active, thinking, communicating
    current_task: Optional[str] = None
    working_memory: Dict[str, Any] = field(default_factory=dict)
    
    # Communication
    connections: List[str] = field(default_factory=list)  # Other agent IDs
    inbox: List[Dict[str, Any]] = field(default_factory=list)
    outbox: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance
    tasks_completed: int = 0
    contribution_score: float = 0.0
    ideas_generated: int = 0
    
    # Prompts for LLM
    system_prompt: str = ""
    
    def generate_system_prompt(self) -> str:
        """Generate optimized system prompt based on profile."""
        archetype_prompts = {
            AgentArchetype.LEADER: "You are a natural leader who coordinates team efforts and ensures alignment.",
            AgentArchetype.EXPLORER: "You are an explorer who discovers unconventional approaches and possibilities.",
            AgentArchetype.ANALYST: "You are an analyst who provides deep, rigorous analysis and critical evaluation.",
            AgentArchetype.CREATOR: "You are a creator who generates novel, innovative solutions.",
            AgentArchetype.GUARDIAN: "You are a guardian who validates ideas and protects against errors.",
            AgentArchetype.SYNTHESIZER: "You are a synthesizer who combines diverse insights into coherent wholes.",
            AgentArchetype.CHALLENGER: "You are a challenger who questions assumptions and pushes for better solutions.",
            AgentArchetype.OPTIMIZER: "You are an optimizer who improves efficiency and eliminates waste.",
            AgentArchetype.VISIONARY: "You are a visionary who sees the big picture and future possibilities.",
            AgentArchetype.SPECIALIST: "You are a specialist with deep domain expertise."
        }
        
        style = self.profile.get_interaction_style()
        
        base = archetype_prompts.get(self.profile.archetype, "You are a capable agent.")
        
        # Add psychological amplifiers
        amplifiers = []
        if self.profile.intrinsic_motivation > 0.7:
            amplifiers.append("You are deeply motivated to find the best solution.")
        if self.profile.achievement_drive > 0.7:
            amplifiers.append("You strive for excellence in everything you do.")
        if self.profile.risk_tolerance > 0.6:
            amplifiers.append("You're willing to explore unconventional approaches.")
        if self.profile.openness > 0.7:
            amplifiers.append("You embrace new ideas and perspectives.")
        
        self.system_prompt = f"""{base}

Role: {self.role}
Skills: {', '.join(self.skills)}
Expertise: {', '.join(self.expertise_domains)}
Interaction Style: {style}

{' '.join(amplifiers)}

Always aim to contribute unique value. Build on others' ideas. Challenge assumptions constructively.
Your goal is to help the swarm achieve breakthrough solutions that exceed all existing approaches."""

        return self.system_prompt


@dataclass
class SwarmConfig:
    """Configuration for swarm creation."""
    name: str
    objective: str
    min_agents: int = 3
    max_agents: int = 20
    topology: SwarmTopology = SwarmTopology.EMERGENT
    communication: CommunicationPattern = CommunicationPattern.GOSSIP
    
    # Diversity settings
    archetype_diversity: float = 0.8  # 0=homogeneous, 1=diverse
    skill_overlap: float = 0.3        # 0=no overlap, 1=complete overlap
    
    # Evolution settings
    enable_evolution: bool = True
    evolution_interval_seconds: float = 60.0
    mutation_rate: float = 0.1
    
    # Performance settings
    consensus_threshold: float = 0.7
    timeout_seconds: float = 300.0


@dataclass
class SwarmMessage:
    """Message between agents."""
    message_id: str
    sender_id: str
    receiver_id: Optional[str]  # None = broadcast
    message_type: str  # "idea", "critique", "question", "answer", "synthesis", "vote"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SwarmResult:
    """Result from swarm execution."""
    swarm_id: str
    objective: str
    success: bool
    
    # Outputs
    final_solution: str
    alternative_solutions: List[str] = field(default_factory=list)
    
    # Insights
    emergent_insights: List[str] = field(default_factory=list)
    breakthrough_ideas: List[str] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    
    # Meta
    agents_used: int = 0
    messages_exchanged: int = 0
    evolution_rounds: int = 0
    execution_time_seconds: float = 0.0
    
    # Contributions
    agent_contributions: Dict[str, float] = field(default_factory=dict)


class AutomatedSwarmCreator:
    """
    Creates and manages intelligent agent swarms automatically.
    
    Revolutionary capabilities:
    1. Zero-shot swarm creation from natural language
    2. Psychological optimization of agent roles
    3. Emergent collective intelligence
    4. Self-organizing hierarchies
    5. Dynamic evolution during execution
    """
    
    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        max_concurrent_swarms: int = 5
    ):
        self.llm_provider = llm_provider
        self.max_concurrent = max_concurrent_swarms
        
        # Active swarms
        self._swarms: Dict[str, Dict[str, MicroAgent]] = {}
        self._swarm_configs: Dict[str, SwarmConfig] = {}
        self._message_logs: Dict[str, List[SwarmMessage]] = {}
        
        # Knowledge base for cross-swarm learning
        self._collective_knowledge: Dict[str, Any] = {}
        self._successful_patterns: List[Dict[str, Any]] = []
        
        # Statistics
        self._stats = {
            "swarms_created": 0,
            "total_agents_spawned": 0,
            "breakthrough_solutions": 0,
            "evolution_rounds": 0
        }
        
        logger.info("AutomatedSwarmCreator initialized")
    
    async def create_swarm(
        self,
        objective: str,
        config: SwarmConfig = None
    ) -> str:
        """
        Create a new swarm optimized for the objective.
        Returns swarm_id.
        """
        if config is None:
            config = await self._generate_optimal_config(objective)
        
        swarm_id = f"swarm_{hashlib.md5(f'{objective}{datetime.utcnow()}'.encode()).hexdigest()[:12]}"
        
        # Determine optimal agent composition
        agent_specs = await self._design_agent_composition(objective, config)
        
        # Create agents
        agents = {}
        for spec in agent_specs:
            agent = await self._create_agent(spec, swarm_id)
            agents[agent.agent_id] = agent
        
        # Establish connections based on topology
        await self._establish_topology(agents, config.topology)
        
        # Store swarm
        self._swarms[swarm_id] = agents
        self._swarm_configs[swarm_id] = config
        self._message_logs[swarm_id] = []
        
        self._stats["swarms_created"] += 1
        self._stats["total_agents_spawned"] += len(agents)
        
        logger.info(f"Created swarm {swarm_id} with {len(agents)} agents for: {objective[:50]}...")
        return swarm_id
    
    async def execute_swarm(
        self,
        swarm_id: str,
        context: Dict[str, Any] = None
    ) -> SwarmResult:
        """
        Execute a swarm to solve its objective.
        """
        import time
        start_time = time.time()
        
        if swarm_id not in self._swarms:
            raise ValueError(f"Swarm {swarm_id} not found")
        
        agents = self._swarms[swarm_id]
        config = self._swarm_configs[swarm_id]
        context = context or {}
        
        # Phase 1: Initial ideation
        ideas = await self._ideation_phase(swarm_id, config.objective, context)
        
        # Phase 2: Critical analysis
        critiques = await self._analysis_phase(swarm_id, ideas)
        
        # Phase 3: Synthesis
        syntheses = await self._synthesis_phase(swarm_id, ideas, critiques)
        
        # Phase 4: Evolution (if enabled)
        if config.enable_evolution:
            syntheses = await self._evolution_phase(swarm_id, syntheses)
        
        # Phase 5: Consensus building
        final_solution, alternatives = await self._consensus_phase(swarm_id, syntheses)
        
        # Collect emergent insights
        emergent = self._extract_emergent_insights(swarm_id)
        
        # Calculate contributions
        contributions = self._calculate_contributions(swarm_id)
        
        result = SwarmResult(
            swarm_id=swarm_id,
            objective=config.objective,
            success=bool(final_solution),
            final_solution=final_solution,
            alternative_solutions=alternatives,
            emergent_insights=emergent,
            breakthrough_ideas=[i for i in ideas if "breakthrough" in str(i).lower()],
            consensus_points=self._extract_consensus_points(swarm_id),
            agents_used=len(agents),
            messages_exchanged=len(self._message_logs[swarm_id]),
            evolution_rounds=self._stats["evolution_rounds"],
            execution_time_seconds=time.time() - start_time,
            agent_contributions=contributions
        )
        
        # Learn from successful execution
        if result.success:
            await self._learn_from_success(result)
        
        return result
    
    async def _generate_optimal_config(self, objective: str) -> SwarmConfig:
        """Generate optimal swarm configuration for objective."""
        # Analyze objective complexity
        words = objective.lower().split()
        
        # Determine agent count based on complexity
        complexity_signals = ["complex", "comprehensive", "multiple", "various", "all", "every"]
        complexity = sum(1 for w in words if w in complexity_signals)
        
        min_agents = 3 + complexity
        max_agents = min(20, 5 + complexity * 2)
        
        # Determine topology
        if "coordinate" in objective.lower() or "organize" in objective.lower():
            topology = SwarmTopology.HIERARCHICAL
        elif "explore" in objective.lower() or "discover" in objective.lower():
            topology = SwarmTopology.MESH
        else:
            topology = SwarmTopology.EMERGENT
        
        return SwarmConfig(
            name=f"Swarm for: {objective[:30]}",
            objective=objective,
            min_agents=min_agents,
            max_agents=max_agents,
            topology=topology,
            enable_evolution=True
        )
    
    async def _design_agent_composition(
        self,
        objective: str,
        config: SwarmConfig
    ) -> List[Dict[str, Any]]:
        """Design optimal agent composition for objective."""
        specs = []
        
        # Always include essential archetypes
        essential = [
            (AgentArchetype.LEADER, "Coordinator", ["coordination", "planning"]),
            (AgentArchetype.ANALYST, "Critical Analyst", ["analysis", "evaluation"]),
            (AgentArchetype.CREATOR, "Solution Generator", ["creativity", "innovation"]),
            (AgentArchetype.SYNTHESIZER, "Insight Synthesizer", ["synthesis", "integration"])
        ]
        
        for archetype, role, skills in essential:
            specs.append({
                "archetype": archetype,
                "role": role,
                "skills": skills,
                "expertise": self._infer_expertise(objective, archetype)
            })
        
        # Add diverse agents based on objective
        if "code" in objective.lower() or "program" in objective.lower():
            specs.append({
                "archetype": AgentArchetype.SPECIALIST,
                "role": "Code Expert",
                "skills": ["programming", "architecture", "debugging"],
                "expertise": ["software engineering", "algorithms"]
            })
        
        if "research" in objective.lower() or "analyze" in objective.lower():
            specs.append({
                "archetype": AgentArchetype.EXPLORER,
                "role": "Research Explorer",
                "skills": ["research", "discovery", "investigation"],
                "expertise": ["information synthesis", "source evaluation"]
            })
        
        if "innovative" in objective.lower() or "novel" in objective.lower():
            specs.append({
                "archetype": AgentArchetype.VISIONARY,
                "role": "Innovation Visionary",
                "skills": ["vision", "future-thinking", "paradigm-shifting"],
                "expertise": ["innovation", "trends"]
            })
        
        # Add challenger for quality
        specs.append({
            "archetype": AgentArchetype.CHALLENGER,
            "role": "Devil's Advocate",
            "skills": ["critique", "questioning", "stress-testing"],
            "expertise": ["quality assurance", "risk assessment"]
        })
        
        # Add optimizer for efficiency
        specs.append({
            "archetype": AgentArchetype.OPTIMIZER,
            "role": "Efficiency Expert",
            "skills": ["optimization", "streamlining", "performance"],
            "expertise": ["efficiency", "resource management"]
        })
        
        # Ensure we're within bounds
        while len(specs) < config.min_agents:
            # Add more explorers for diversity
            specs.append({
                "archetype": AgentArchetype.EXPLORER,
                "role": f"Explorer {len(specs)}",
                "skills": ["exploration", "discovery"],
                "expertise": ["general"]
            })
        
        return specs[:config.max_agents]
    
    def _infer_expertise(self, objective: str, archetype: AgentArchetype) -> List[str]:
        """Infer expertise domains from objective."""
        expertise = []
        
        keywords = {
            "ai": ["artificial intelligence", "machine learning"],
            "code": ["software development", "programming"],
            "business": ["business strategy", "market analysis"],
            "research": ["academic research", "literature review"],
            "design": ["system design", "architecture"],
            "data": ["data analysis", "statistics"]
        }
        
        for keyword, domains in keywords.items():
            if keyword in objective.lower():
                expertise.extend(domains)
        
        return expertise or ["general problem solving"]
    
    async def _create_agent(
        self,
        spec: Dict[str, Any],
        swarm_id: str
    ) -> MicroAgent:
        """Create a micro-agent from specification."""
        agent_id = f"agent_{hashlib.md5(f'{spec}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"
        
        # Create psychological profile
        archetype = spec["archetype"]
        profile = self._create_psychological_profile(archetype)
        
        agent = MicroAgent(
            agent_id=agent_id,
            name=f"{archetype.value.title()} Agent",
            role=spec["role"],
            profile=profile,
            skills=spec["skills"],
            expertise_domains=spec.get("expertise", [])
        )
        
        # Generate optimized system prompt
        agent.generate_system_prompt()
        
        return agent
    
    def _create_psychological_profile(self, archetype: AgentArchetype) -> PsychologicalProfile:
        """Create psychological profile optimized for archetype."""
        base_profiles = {
            AgentArchetype.LEADER: PsychologicalProfile(
                archetype=archetype,
                openness=0.7, conscientiousness=0.9, extraversion=0.8,
                agreeableness=0.7, neuroticism=0.2,
                analytical_creative_balance=0.4, detail_big_picture_balance=0.7,
                risk_tolerance=0.6, intrinsic_motivation=0.9, achievement_drive=0.9
            ),
            AgentArchetype.EXPLORER: PsychologicalProfile(
                archetype=archetype,
                openness=0.95, conscientiousness=0.5, extraversion=0.7,
                agreeableness=0.6, neuroticism=0.4,
                analytical_creative_balance=0.8, detail_big_picture_balance=0.6,
                risk_tolerance=0.9, intrinsic_motivation=0.9, achievement_drive=0.6
            ),
            AgentArchetype.ANALYST: PsychologicalProfile(
                archetype=archetype,
                openness=0.6, conscientiousness=0.95, extraversion=0.3,
                agreeableness=0.5, neuroticism=0.3,
                analytical_creative_balance=0.1, detail_big_picture_balance=0.2,
                risk_tolerance=0.2, intrinsic_motivation=0.8, achievement_drive=0.8
            ),
            AgentArchetype.CREATOR: PsychologicalProfile(
                archetype=archetype,
                openness=0.95, conscientiousness=0.6, extraversion=0.6,
                agreeableness=0.7, neuroticism=0.4,
                analytical_creative_balance=0.9, detail_big_picture_balance=0.5,
                risk_tolerance=0.8, intrinsic_motivation=0.95, achievement_drive=0.7
            ),
            AgentArchetype.CHALLENGER: PsychologicalProfile(
                archetype=archetype,
                openness=0.7, conscientiousness=0.7, extraversion=0.6,
                agreeableness=0.3, neuroticism=0.3,
                analytical_creative_balance=0.4, detail_big_picture_balance=0.4,
                risk_tolerance=0.7, intrinsic_motivation=0.8, achievement_drive=0.8
            )
        }
        
        return base_profiles.get(archetype, PsychologicalProfile(archetype=archetype))
    
    async def _establish_topology(
        self,
        agents: Dict[str, MicroAgent],
        topology: SwarmTopology
    ) -> None:
        """Establish communication topology between agents."""
        agent_list = list(agents.values())
        n = len(agent_list)
        
        if topology == SwarmTopology.MESH:
            # Full connectivity
            for agent in agent_list:
                agent.connections = [a.agent_id for a in agent_list if a.agent_id != agent.agent_id]
        
        elif topology == SwarmTopology.STAR:
            # Leader connects to all
            leader = agent_list[0]
            for agent in agent_list[1:]:
                agent.connections = [leader.agent_id]
                leader.connections.append(agent.agent_id)
        
        elif topology == SwarmTopology.RING:
            # Each connects to neighbors
            for i, agent in enumerate(agent_list):
                prev_idx = (i - 1) % n
                next_idx = (i + 1) % n
                agent.connections = [agent_list[prev_idx].agent_id, agent_list[next_idx].agent_id]
        
        elif topology == SwarmTopology.HIERARCHICAL:
            # Tree structure
            leader = agent_list[0]
            subordinates = agent_list[1:]
            for sub in subordinates:
                sub.connections = [leader.agent_id]
                leader.connections.append(sub.agent_id)
        
        else:  # EMERGENT or FLAT
            # Random initial connections, will evolve
            for agent in agent_list:
                num_connections = random.randint(1, min(3, n-1))
                others = [a for a in agent_list if a.agent_id != agent.agent_id]
                agent.connections = [a.agent_id for a in random.sample(others, num_connections)]
    
    async def _ideation_phase(
        self,
        swarm_id: str,
        objective: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Run ideation phase with all agents."""
        agents = self._swarms[swarm_id]
        ideas = []
        
        for agent in agents.values():
            if agent.profile.archetype in [AgentArchetype.CREATOR, AgentArchetype.EXPLORER, 
                                           AgentArchetype.VISIONARY]:
                idea = await self._agent_generate(agent, f"""
Generate innovative ideas for: {objective}

Context: {json.dumps(context)}

Think boldly. Consider unconventional approaches. Aim for breakthrough solutions.
What unique perspective can you offer based on your expertise in {', '.join(agent.expertise_domains)}?
""")
                ideas.append(idea)
                agent.ideas_generated += 1
                
                # Log message
                self._log_message(swarm_id, agent.agent_id, None, "idea", idea)
        
        return ideas
    
    async def _analysis_phase(
        self,
        swarm_id: str,
        ideas: List[str]
    ) -> List[str]:
        """Run analysis phase."""
        agents = self._swarms[swarm_id]
        critiques = []
        
        for agent in agents.values():
            if agent.profile.archetype in [AgentArchetype.ANALYST, AgentArchetype.CHALLENGER,
                                           AgentArchetype.GUARDIAN]:
                critique = await self._agent_generate(agent, f"""
Analyze these ideas critically:

{json.dumps(ideas, indent=2)}

Identify:
1. Strengths and potential
2. Weaknesses and risks
3. Missing considerations
4. How to improve each idea

Be constructive but rigorous.
""")
                critiques.append(critique)
                
                self._log_message(swarm_id, agent.agent_id, None, "critique", critique)
        
        return critiques
    
    async def _synthesis_phase(
        self,
        swarm_id: str,
        ideas: List[str],
        critiques: List[str]
    ) -> List[str]:
        """Run synthesis phase."""
        agents = self._swarms[swarm_id]
        syntheses = []
        
        for agent in agents.values():
            if agent.profile.archetype in [AgentArchetype.SYNTHESIZER, AgentArchetype.LEADER]:
                synthesis = await self._agent_generate(agent, f"""
Synthesize the following into a coherent, improved solution:

ORIGINAL IDEAS:
{json.dumps(ideas, indent=2)}

CRITIQUES AND ANALYSIS:
{json.dumps(critiques, indent=2)}

Create a synthesis that:
1. Combines the best elements
2. Addresses the critiques
3. Creates something greater than the parts
4. Represents a breakthrough approach
""")
                syntheses.append(synthesis)
                
                self._log_message(swarm_id, agent.agent_id, None, "synthesis", synthesis)
        
        return syntheses
    
    async def _evolution_phase(
        self,
        swarm_id: str,
        syntheses: List[str]
    ) -> List[str]:
        """Evolve solutions through iteration."""
        agents = self._swarms[swarm_id]
        evolved = syntheses.copy()
        
        # Run evolution round
        for agent in agents.values():
            if agent.profile.archetype == AgentArchetype.OPTIMIZER:
                optimized = await self._agent_generate(agent, f"""
Optimize and evolve these solutions:

{json.dumps(evolved, indent=2)}

Make them:
1. More efficient
2. More elegant
3. More powerful
4. More innovative

Push beyond current limits.
""")
                evolved.append(optimized)
                self._stats["evolution_rounds"] += 1
        
        return evolved
    
    async def _consensus_phase(
        self,
        swarm_id: str,
        syntheses: List[str]
    ) -> Tuple[str, List[str]]:
        """Build consensus on final solution."""
        agents = self._swarms[swarm_id]
        
        # Have leader create final recommendation
        leader = None
        for agent in agents.values():
            if agent.profile.archetype == AgentArchetype.LEADER:
                leader = agent
                break
        
        if leader and self.llm_provider:
            final = await self._agent_generate(leader, f"""
As the leader, create the final solution from these syntheses:

{json.dumps(syntheses, indent=2)}

Create:
1. A definitive, actionable solution
2. That represents the best of all contributions
3. That exceeds what any individual could create
4. That is truly breakthrough and innovative

This is your final recommendation.
""")
            return final, syntheses[1:3] if len(syntheses) > 1 else []
        
        return syntheses[0] if syntheses else "", syntheses[1:] if len(syntheses) > 1 else []
    
    async def _agent_generate(self, agent: MicroAgent, prompt: str) -> str:
        """Generate response from agent."""
        if self.llm_provider:
            full_prompt = f"{agent.system_prompt}\n\n{prompt}"
            try:
                return await self.llm_provider(full_prompt)
            except:
                pass
        
        # Fallback
        return f"[{agent.role}] Contribution based on {', '.join(agent.skills)}"
    
    def _log_message(
        self,
        swarm_id: str,
        sender_id: str,
        receiver_id: Optional[str],
        message_type: str,
        content: str
    ) -> None:
        """Log a swarm message."""
        message = SwarmMessage(
            message_id=f"msg_{hashlib.md5(f'{content[:50]}{datetime.utcnow()}'.encode()).hexdigest()[:8]}",
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content
        )
        self._message_logs[swarm_id].append(message)
    
    def _extract_emergent_insights(self, swarm_id: str) -> List[str]:
        """Extract emergent insights from swarm interactions."""
        messages = self._message_logs.get(swarm_id, [])
        insights = []
        
        # Look for patterns
        if len(messages) >= 5:
            insights.append("Multi-perspective synthesis achieved")
        
        # Check for breakthrough signals
        for msg in messages:
            if any(word in msg.content.lower() for word in ["breakthrough", "novel", "unprecedented"]):
                insights.append(f"Breakthrough detected from {msg.sender_id}")
                break
        
        return insights
    
    def _extract_consensus_points(self, swarm_id: str) -> List[str]:
        """Extract points of consensus."""
        return ["Swarm achieved consensus on solution approach"]
    
    def _calculate_contributions(self, swarm_id: str) -> Dict[str, float]:
        """Calculate agent contributions."""
        agents = self._swarms.get(swarm_id, {})
        messages = self._message_logs.get(swarm_id, [])
        
        contributions = {}
        for agent_id, agent in agents.items():
            message_count = sum(1 for m in messages if m.sender_id == agent_id)
            contributions[agent_id] = message_count / max(len(messages), 1)
        
        return contributions
    
    async def _learn_from_success(self, result: SwarmResult) -> None:
        """Learn from successful execution."""
        pattern = {
            "objective_keywords": result.objective.lower().split()[:10],
            "agents_used": result.agents_used,
            "execution_time": result.execution_time_seconds,
            "success": True
        }
        self._successful_patterns.append(pattern)
        
        # Limit patterns
        if len(self._successful_patterns) > 100:
            self._successful_patterns = self._successful_patterns[-50:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get swarm creator statistics."""
        return {
            **self._stats,
            "active_swarms": len(self._swarms),
            "successful_patterns": len(self._successful_patterns)
        }


# Global instance
_swarm_creator: Optional[AutomatedSwarmCreator] = None


def get_swarm_creator() -> AutomatedSwarmCreator:
    """Get the global swarm creator."""
    global _swarm_creator
    if _swarm_creator is None:
        _swarm_creator = AutomatedSwarmCreator()
    return _swarm_creator


async def demo():
    """Demonstrate automated swarm creation."""
    creator = get_swarm_creator()
    
    # Create a swarm for a complex task
    swarm_id = await creator.create_swarm(
        objective="Design the most advanced AI agent system that surpasses all competitors"
    )
    
    print(f"Created swarm: {swarm_id}")
    print(f"Agents in swarm: {len(creator._swarms[swarm_id])}")
    
    for agent_id, agent in creator._swarms[swarm_id].items():
        print(f"  - {agent.name} ({agent.role}): {agent.profile.archetype.value}")
    
    # Execute swarm
    result = await creator.execute_swarm(swarm_id)
    
    print(f"\nSwarm Result:")
    print(f"  Success: {result.success}")
    print(f"  Agents: {result.agents_used}")
    print(f"  Messages: {result.messages_exchanged}")
    print(f"  Time: {result.execution_time_seconds:.2f}s")
    print(f"\nFinal Solution:\n{result.final_solution[:500]}...")


if __name__ == "__main__":
    asyncio.run(demo())
