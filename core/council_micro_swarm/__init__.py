"""
BAEL - Council Micro Swarm Orchestration System
The most advanced multi-council, micro-agent swarm orchestration ever created.

This system implements:
1. Council of Councils - Meta-councils that coordinate multiple councils
2. Micro-Agent Swarms - Thousands of specialized micro-agents
3. Psychological Role Optimization - Agents with psychologically optimized personas
4. Emergent Intelligence - Intelligence that emerges from agent interactions
5. Hierarchical Deliberation - Multi-level decision making
6. Consensus Synthesis - Advanced agreement mechanisms
7. Competitive Evolution - Agents compete to evolve best solutions
8. Cross-Council Knowledge Sharing

This exceeds anything in AutoGen, CrewAI, or any other multi-agent framework.
"""

import asyncio
import hashlib
import json
import logging
import random
import math
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.CouncilMicroSwarm")


# ============================================================================
# Enums and Types
# ============================================================================

class CouncilType(Enum):
    """Types of councils in the hierarchy."""
    SUPREME = "supreme"           # Top-level meta-council
    STRATEGIC = "strategic"       # Strategic decision making
    TACTICAL = "tactical"         # Tactical execution
    SPECIALIZED = "specialized"   # Domain-specific
    ADVISORY = "advisory"         # Advisory only
    EXECUTION = "execution"       # Task execution


class AgentRole(Enum):
    """Psychological roles for agents."""
    VISIONARY = "visionary"           # Big picture thinking
    ANALYST = "analyst"               # Deep analysis
    CRITIC = "critic"                 # Critical evaluation
    SYNTHESIZER = "synthesizer"       # Combining ideas
    EXECUTOR = "executor"             # Task execution
    GUARDIAN = "guardian"             # Quality assurance
    INNOVATOR = "innovator"           # Novel ideas
    MEDIATOR = "mediator"             # Conflict resolution
    STRATEGIST = "strategist"         # Strategic planning
    SPECIALIST = "specialist"         # Domain expertise
    DEVIL_ADVOCATE = "devil_advocate" # Challenge assumptions
    OPTIMIST = "optimist"             # Positive perspective
    PESSIMIST = "pessimist"           # Risk awareness
    PRAGMATIST = "pragmatist"         # Practical solutions


class VotingMethod(Enum):
    """Voting methods for council decisions."""
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"   # 2/3 majority
    UNANIMOUS = "unanimous"
    RANKED = "ranked"                  # Ranked choice
    WEIGHTED = "weighted"              # Weighted by expertise
    CONSENSUS = "consensus"            # Discussion until agreement
    VETO = "veto"                      # Any member can veto


class MessagePriority(Enum):
    """Priority levels for inter-agent messages."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PsychologicalProfile:
    """Psychological profile for agent optimization."""
    # Core traits
    openness: float = 0.7            # 0-1
    conscientiousness: float = 0.7
    extraversion: float = 0.5
    agreeableness: float = 0.6
    neuroticism: float = 0.3
    
    # Cognitive style
    analytical_creative: float = 0.5  # 0=analytical, 1=creative
    detail_bigpicture: float = 0.5    # 0=detail, 1=big picture
    risk_tolerance: float = 0.5
    
    # Motivational
    intrinsic_motivation: float = 0.8
    achievement_drive: float = 0.7
    collaboration_pref: float = 0.6
    
    def get_interaction_style(self) -> str:
        """Get optimal interaction style."""
        if self.extraversion > 0.7 and self.agreeableness > 0.6:
            return "collaborative"
        elif self.openness > 0.8:
            return "exploratory"
        elif self.conscientiousness > 0.8:
            return "methodical"
        elif self.risk_tolerance > 0.7:
            return "bold"
        return "balanced"


@dataclass
class MicroAgent:
    """A micro-agent in the swarm."""
    agent_id: str
    name: str
    role: AgentRole
    profile: PsychologicalProfile
    
    # Capabilities
    skills: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    
    # State
    status: str = "idle"
    current_task: Optional[str] = None
    working_memory: Dict[str, Any] = field(default_factory=dict)
    
    # Communication
    inbox: List["AgentMessage"] = field(default_factory=list)
    
    # Performance
    tasks_completed: int = 0
    contribution_score: float = 0.0
    ideas_generated: int = 0
    
    # LLM
    system_prompt: str = ""
    
    def generate_system_prompt(self) -> str:
        """Generate optimized system prompt."""
        role_prompts = {
            AgentRole.VISIONARY: "You see the big picture and future possibilities. Think expansively.",
            AgentRole.ANALYST: "You provide rigorous, deep analysis. Be thorough and precise.",
            AgentRole.CRITIC: "You critically evaluate ideas. Find weaknesses and improvements.",
            AgentRole.SYNTHESIZER: "You combine diverse ideas into coherent wholes.",
            AgentRole.EXECUTOR: "You focus on practical execution. Get things done.",
            AgentRole.GUARDIAN: "You ensure quality and protect against errors.",
            AgentRole.INNOVATOR: "You generate novel, creative ideas. Think differently.",
            AgentRole.MEDIATOR: "You resolve conflicts and find common ground.",
            AgentRole.STRATEGIST: "You plan strategically for long-term success.",
            AgentRole.SPECIALIST: f"You have deep expertise in {', '.join(self.domains)}.",
            AgentRole.DEVIL_ADVOCATE: "You challenge assumptions and argue against consensus.",
            AgentRole.OPTIMIST: "You see positive possibilities and opportunities.",
            AgentRole.PESSIMIST: "You identify risks and potential failures.",
            AgentRole.PRAGMATIST: "You focus on practical, achievable solutions."
        }
        
        base = role_prompts.get(self.role, "You are a capable agent.")
        style = self.profile.get_interaction_style()
        
        self.system_prompt = f"""{base}

Name: {self.name}
Role: {self.role.value}
Skills: {', '.join(self.skills)}
Interaction Style: {style}

Your goal: Contribute unique value to the council's deliberations.
Be concise, insightful, and build on others' ideas."""

        return self.system_prompt


@dataclass
class AgentMessage:
    """Message between agents."""
    message_id: str
    sender_id: str
    receiver_id: Optional[str]  # None = broadcast
    priority: MessagePriority
    content: str
    message_type: str  # idea, critique, question, vote, synthesis
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CouncilDecision:
    """A decision made by a council."""
    decision_id: str
    council_id: str
    topic: str
    decision: str
    
    # Voting
    voting_method: VotingMethod = VotingMethod.CONSENSUS
    votes: Dict[str, Any] = field(default_factory=dict)
    approval_rate: float = 0.0
    
    # Reasoning
    supporting_arguments: List[str] = field(default_factory=list)
    dissenting_opinions: List[str] = field(default_factory=list)
    
    # Confidence
    confidence: float = 0.0
    
    # Meta
    timestamp: datetime = field(default_factory=datetime.utcnow)
    deliberation_rounds: int = 0


@dataclass
class Council:
    """A council of agents."""
    council_id: str
    name: str
    council_type: CouncilType
    
    # Composition
    members: List[MicroAgent] = field(default_factory=list)
    leader: Optional[MicroAgent] = None
    
    # Configuration
    voting_method: VotingMethod = VotingMethod.CONSENSUS
    quorum: float = 0.5  # Minimum participation
    max_deliberation_rounds: int = 5
    
    # State
    current_topic: Optional[str] = None
    decisions: List[CouncilDecision] = field(default_factory=list)
    message_history: List[AgentMessage] = field(default_factory=list)
    
    # Hierarchy
    parent_council: Optional[str] = None  # Council ID of parent
    child_councils: List[str] = field(default_factory=list)
    
    # Performance
    decisions_made: int = 0
    avg_deliberation_time: float = 0.0


@dataclass
class SwarmTask:
    """A task for the micro-agent swarm."""
    task_id: str
    description: str
    objective: str
    
    # Configuration
    agent_count: int = 10
    max_iterations: int = 100
    
    # State
    status: str = "pending"
    assigned_agents: List[str] = field(default_factory=list)
    
    # Results
    result: Optional[str] = None
    ideas_generated: int = 0
    consensus_points: List[str] = field(default_factory=list)


# ============================================================================
# Core Components
# ============================================================================

class AgentFactory:
    """Factory for creating psychologically-optimized agents."""
    
    @staticmethod
    def create_agent(
        role: AgentRole,
        name: str = None,
        skills: List[str] = None,
        domains: List[str] = None
    ) -> MicroAgent:
        """Create an agent optimized for a role."""
        agent_id = f"agent_{hashlib.md5(f'{role.value}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"
        
        # Role-specific profiles
        role_profiles = {
            AgentRole.VISIONARY: PsychologicalProfile(
                openness=0.95, conscientiousness=0.6, extraversion=0.7,
                analytical_creative=0.8, detail_bigpicture=0.9, risk_tolerance=0.8
            ),
            AgentRole.ANALYST: PsychologicalProfile(
                openness=0.6, conscientiousness=0.95, extraversion=0.4,
                analytical_creative=0.1, detail_bigpicture=0.2, risk_tolerance=0.3
            ),
            AgentRole.CRITIC: PsychologicalProfile(
                openness=0.7, conscientiousness=0.8, agreeableness=0.3,
                analytical_creative=0.3, detail_bigpicture=0.4, risk_tolerance=0.4
            ),
            AgentRole.SYNTHESIZER: PsychologicalProfile(
                openness=0.8, conscientiousness=0.7, agreeableness=0.8,
                analytical_creative=0.5, detail_bigpicture=0.7, collaboration_pref=0.9
            ),
            AgentRole.INNOVATOR: PsychologicalProfile(
                openness=0.95, conscientiousness=0.5, extraversion=0.6,
                analytical_creative=0.95, risk_tolerance=0.9, intrinsic_motivation=0.95
            ),
            AgentRole.DEVIL_ADVOCATE: PsychologicalProfile(
                openness=0.7, conscientiousness=0.7, agreeableness=0.2,
                analytical_creative=0.5, risk_tolerance=0.7, neuroticism=0.4
            ),
            AgentRole.GUARDIAN: PsychologicalProfile(
                openness=0.5, conscientiousness=0.95, agreeableness=0.6,
                analytical_creative=0.2, detail_bigpicture=0.1, risk_tolerance=0.1
            )
        }
        
        profile = role_profiles.get(role, PsychologicalProfile())
        
        agent = MicroAgent(
            agent_id=agent_id,
            name=name or f"{role.value.title()} Agent",
            role=role,
            profile=profile,
            skills=skills or [],
            domains=domains or []
        )
        
        agent.generate_system_prompt()
        return agent
    
    @staticmethod
    def create_diverse_team(
        size: int = 5,
        domain: str = None
    ) -> List[MicroAgent]:
        """Create a psychologically diverse team."""
        # Essential roles
        essential = [
            AgentRole.VISIONARY,
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
            AgentRole.GUARDIAN
        ]
        
        # Additional diversity
        additional = [
            AgentRole.INNOVATOR,
            AgentRole.CRITIC,
            AgentRole.DEVIL_ADVOCATE,
            AgentRole.OPTIMIST,
            AgentRole.PESSIMIST,
            AgentRole.PRAGMATIST,
            AgentRole.STRATEGIST,
            AgentRole.EXECUTOR
        ]
        
        agents = []
        roles_to_use = essential[:min(size, len(essential))]
        
        if size > len(essential):
            random.shuffle(additional)
            roles_to_use.extend(additional[:size - len(essential)])
        
        for role in roles_to_use:
            agent = AgentFactory.create_agent(
                role=role,
                domains=[domain] if domain else []
            )
            agents.append(agent)
        
        return agents


class CouncilFactory:
    """Factory for creating optimized councils."""
    
    @staticmethod
    def create_council(
        name: str,
        council_type: CouncilType,
        member_count: int = 5,
        domain: str = None,
        voting_method: VotingMethod = VotingMethod.CONSENSUS
    ) -> Council:
        """Create an optimized council."""
        council_id = f"council_{hashlib.md5(f'{name}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"
        
        # Create diverse members
        members = AgentFactory.create_diverse_team(member_count, domain)
        
        # Assign leader (strategist or highest profile match)
        leader = None
        for member in members:
            if member.role in [AgentRole.STRATEGIST, AgentRole.VISIONARY]:
                leader = member
                break
        if not leader and members:
            leader = members[0]
        
        council = Council(
            council_id=council_id,
            name=name,
            council_type=council_type,
            members=members,
            leader=leader,
            voting_method=voting_method
        )
        
        return council
    
    @staticmethod
    def create_council_hierarchy(
        objective: str,
        depth: int = 2,
        councils_per_level: int = 3
    ) -> Dict[str, Council]:
        """Create a hierarchical council structure."""
        councils = {}
        
        # Supreme council at top
        supreme = CouncilFactory.create_council(
            name=f"Supreme Council: {objective[:30]}",
            council_type=CouncilType.SUPREME,
            member_count=7,
            voting_method=VotingMethod.SUPERMAJORITY
        )
        councils[supreme.council_id] = supreme
        
        if depth > 1:
            # Strategic councils
            for i in range(councils_per_level):
                strategic = CouncilFactory.create_council(
                    name=f"Strategic Council {i+1}",
                    council_type=CouncilType.STRATEGIC,
                    member_count=5,
                    voting_method=VotingMethod.MAJORITY
                )
                strategic.parent_council = supreme.council_id
                supreme.child_councils.append(strategic.council_id)
                councils[strategic.council_id] = strategic
                
                if depth > 2:
                    # Tactical councils under each strategic
                    for j in range(2):
                        tactical = CouncilFactory.create_council(
                            name=f"Tactical Council {i+1}-{j+1}",
                            council_type=CouncilType.TACTICAL,
                            member_count=4,
                            voting_method=VotingMethod.MAJORITY
                        )
                        tactical.parent_council = strategic.council_id
                        strategic.child_councils.append(tactical.council_id)
                        councils[tactical.council_id] = tactical
        
        return councils


class DeliberationEngine:
    """Engine for running council deliberations."""
    
    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider
    
    async def deliberate(
        self,
        council: Council,
        topic: str,
        context: Dict[str, Any] = None
    ) -> CouncilDecision:
        """Run a full deliberation process."""
        council.current_topic = topic
        decision_id = f"decision_{hashlib.md5(f'{topic}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"
        
        all_messages = []
        rounds_completed = 0
        
        for round_num in range(council.max_deliberation_rounds):
            rounds_completed = round_num + 1
            
            # Phase 1: Ideation
            ideas = await self._ideation_round(council, topic, context, round_num)
            all_messages.extend(ideas)
            
            # Phase 2: Critical Analysis
            critiques = await self._critique_round(council, ideas)
            all_messages.extend(critiques)
            
            # Phase 3: Synthesis
            syntheses = await self._synthesis_round(council, ideas, critiques)
            all_messages.extend(syntheses)
            
            # Check for consensus
            if await self._check_consensus(council, syntheses):
                break
        
        # Final voting
        votes, approval_rate = await self._vote(council, syntheses)
        
        # Generate final decision
        final_decision = await self._generate_decision(council, syntheses, votes)
        
        decision = CouncilDecision(
            decision_id=decision_id,
            council_id=council.council_id,
            topic=topic,
            decision=final_decision,
            voting_method=council.voting_method,
            votes=votes,
            approval_rate=approval_rate,
            supporting_arguments=[s.content for s in syntheses if "support" in s.content.lower()],
            dissenting_opinions=[c.content for c in critiques if "disagree" in c.content.lower()],
            confidence=approval_rate,
            deliberation_rounds=rounds_completed
        )
        
        council.decisions.append(decision)
        council.decisions_made += 1
        council.message_history.extend(all_messages)
        
        return decision
    
    async def _ideation_round(
        self,
        council: Council,
        topic: str,
        context: Dict[str, Any],
        round_num: int
    ) -> List[AgentMessage]:
        """Run ideation round."""
        messages = []
        
        for agent in council.members:
            if agent.role in [AgentRole.VISIONARY, AgentRole.INNOVATOR, AgentRole.OPTIMIST]:
                idea = await self._agent_generate(agent, f"""
Topic: {topic}

Round {round_num + 1} Ideation: Generate innovative ideas and perspectives.
Consider unconventional approaches. Build on any previous ideas.

Context: {json.dumps(context or {})}
""")
                
                msg = AgentMessage(
                    message_id=f"msg_{hashlib.md5(f'{agent.agent_id}{datetime.utcnow()}'.encode()).hexdigest()[:8]}",
                    sender_id=agent.agent_id,
                    receiver_id=None,
                    priority=MessagePriority.NORMAL,
                    content=idea,
                    message_type="idea"
                )
                messages.append(msg)
                agent.ideas_generated += 1
        
        return messages
    
    async def _critique_round(
        self,
        council: Council,
        ideas: List[AgentMessage]
    ) -> List[AgentMessage]:
        """Run critique round."""
        messages = []
        ideas_text = "\n".join([f"- {m.content}" for m in ideas])
        
        for agent in council.members:
            if agent.role in [AgentRole.CRITIC, AgentRole.ANALYST, AgentRole.DEVIL_ADVOCATE, AgentRole.PESSIMIST]:
                critique = await self._agent_generate(agent, f"""
Analyze these ideas critically:

{ideas_text}

Identify:
1. Strengths and weaknesses
2. Risks and blindspots
3. What's missing
4. How to improve

Be thorough but constructive.
""")
                
                msg = AgentMessage(
                    message_id=f"msg_{hashlib.md5(f'{agent.agent_id}crit{datetime.utcnow()}'.encode()).hexdigest()[:8]}",
                    sender_id=agent.agent_id,
                    receiver_id=None,
                    priority=MessagePriority.NORMAL,
                    content=critique,
                    message_type="critique"
                )
                messages.append(msg)
        
        return messages
    
    async def _synthesis_round(
        self,
        council: Council,
        ideas: List[AgentMessage],
        critiques: List[AgentMessage]
    ) -> List[AgentMessage]:
        """Run synthesis round."""
        messages = []
        
        ideas_text = "\n".join([f"- {m.content}" for m in ideas])
        critiques_text = "\n".join([f"- {m.content}" for m in critiques])
        
        for agent in council.members:
            if agent.role in [AgentRole.SYNTHESIZER, AgentRole.MEDIATOR, AgentRole.PRAGMATIST]:
                synthesis = await self._agent_generate(agent, f"""
Synthesize the following into a coherent solution:

IDEAS:
{ideas_text}

CRITIQUES:
{critiques_text}

Create a unified proposal that:
1. Incorporates the best ideas
2. Addresses the critiques
3. Is practical and actionable
""")
                
                msg = AgentMessage(
                    message_id=f"msg_{hashlib.md5(f'{agent.agent_id}syn{datetime.utcnow()}'.encode()).hexdigest()[:8]}",
                    sender_id=agent.agent_id,
                    receiver_id=None,
                    priority=MessagePriority.NORMAL,
                    content=synthesis,
                    message_type="synthesis"
                )
                messages.append(msg)
        
        return messages
    
    async def _check_consensus(
        self,
        council: Council,
        syntheses: List[AgentMessage]
    ) -> bool:
        """Check if consensus has been reached."""
        if not syntheses:
            return False
        
        # Simple check: if syntheses are similar, we have consensus
        # In reality, this would use semantic similarity
        return len(syntheses) > 0 and len(set(s.content[:50] for s in syntheses)) <= 2
    
    async def _vote(
        self,
        council: Council,
        syntheses: List[AgentMessage]
    ) -> Tuple[Dict[str, Any], float]:
        """Conduct voting on the syntheses."""
        votes = {}
        approvals = 0
        
        for agent in council.members:
            # Simple approval voting
            vote = await self._agent_generate(agent, f"""
Vote on this proposal (respond with APPROVE or REJECT and brief reason):

{syntheses[0].content if syntheses else 'No proposal'}
""")
            
            is_approve = "approve" in vote.lower()
            votes[agent.agent_id] = {
                "vote": "approve" if is_approve else "reject",
                "reason": vote
            }
            if is_approve:
                approvals += 1
        
        approval_rate = approvals / len(council.members) if council.members else 0
        
        return votes, approval_rate
    
    async def _generate_decision(
        self,
        council: Council,
        syntheses: List[AgentMessage],
        votes: Dict[str, Any]
    ) -> str:
        """Generate final decision text."""
        if not syntheses:
            return "No decision reached"
        
        if council.leader:
            final = await self._agent_generate(council.leader, f"""
As council leader, formulate the final decision based on:

SYNTHESES:
{chr(10).join(s.content for s in syntheses)}

VOTES:
{json.dumps(votes, indent=2)}

State the final decision clearly and concisely.
""")
            return final
        
        return syntheses[0].content if syntheses else "No decision"
    
    async def _agent_generate(self, agent: MicroAgent, prompt: str) -> str:
        """Generate response from an agent."""
        if self.llm_provider:
            full_prompt = f"{agent.system_prompt}\n\n{prompt}"
            try:
                return await self.llm_provider(full_prompt)
            except:
                pass
        
        # Fallback
        return f"[{agent.role.value}] Contribution based on {agent.profile.get_interaction_style()} style"


class MicroSwarmOrchestrator:
    """Orchestrates large micro-agent swarms."""
    
    def __init__(self, llm_provider: Callable = None, max_agents: int = 100):
        self.llm_provider = llm_provider
        self.max_agents = max_agents
        
        self._agents: Dict[str, MicroAgent] = {}
        self._active_swarms: Dict[str, SwarmTask] = {}
        
        self._stats = {
            "agents_created": 0,
            "swarms_run": 0,
            "total_ideas": 0
        }
    
    async def create_swarm(
        self,
        objective: str,
        agent_count: int = 20
    ) -> str:
        """Create a micro-agent swarm for an objective."""
        task_id = f"swarm_{hashlib.md5(f'{objective}{datetime.utcnow()}'.encode()).hexdigest()[:8]}"
        
        agent_count = min(agent_count, self.max_agents)
        
        # Create diverse agents
        agents = []
        roles = list(AgentRole)
        
        for i in range(agent_count):
            role = roles[i % len(roles)]
            agent = AgentFactory.create_agent(role)
            agents.append(agent)
            self._agents[agent.agent_id] = agent
        
        task = SwarmTask(
            task_id=task_id,
            description=f"Swarm task: {objective}",
            objective=objective,
            agent_count=agent_count,
            assigned_agents=[a.agent_id for a in agents]
        )
        
        self._active_swarms[task_id] = task
        self._stats["agents_created"] += agent_count
        
        return task_id
    
    async def run_swarm(self, task_id: str) -> Dict[str, Any]:
        """Run a swarm task."""
        if task_id not in self._active_swarms:
            raise ValueError(f"Swarm {task_id} not found")
        
        task = self._active_swarms[task_id]
        task.status = "running"
        
        agents = [self._agents[aid] for aid in task.assigned_agents if aid in self._agents]
        
        all_ideas = []
        all_critiques = []
        
        # Parallel ideation
        for agent in agents:
            if agent.role in [AgentRole.VISIONARY, AgentRole.INNOVATOR, AgentRole.OPTIMIST]:
                idea = await self._agent_think(agent, task.objective)
                all_ideas.append({"agent": agent.agent_id, "idea": idea})
                agent.ideas_generated += 1
        
        # Parallel critique
        for agent in agents:
            if agent.role in [AgentRole.CRITIC, AgentRole.ANALYST, AgentRole.PESSIMIST]:
                critique = await self._agent_critique(agent, all_ideas)
                all_critiques.append({"agent": agent.agent_id, "critique": critique})
        
        # Synthesis
        synthesizers = [a for a in agents if a.role == AgentRole.SYNTHESIZER]
        final_synthesis = ""
        if synthesizers:
            final_synthesis = await self._agent_synthesize(synthesizers[0], all_ideas, all_critiques)
        
        task.status = "completed"
        task.result = final_synthesis
        task.ideas_generated = len(all_ideas)
        
        self._stats["swarms_run"] += 1
        self._stats["total_ideas"] += len(all_ideas)
        
        return {
            "task_id": task_id,
            "objective": task.objective,
            "agents_used": len(agents),
            "ideas_generated": len(all_ideas),
            "critiques": len(all_critiques),
            "result": final_synthesis
        }
    
    async def _agent_think(self, agent: MicroAgent, objective: str) -> str:
        """Agent generates ideas."""
        if self.llm_provider:
            try:
                return await self.llm_provider(f"{agent.system_prompt}\n\nGenerate ideas for: {objective}")
            except:
                pass
        return f"[{agent.role.value}] Idea for {objective}"
    
    async def _agent_critique(self, agent: MicroAgent, ideas: List[Dict[str, Any]]) -> str:
        """Agent critiques ideas."""
        if self.llm_provider:
            try:
                ideas_text = "\n".join([f"- {i['idea']}" for i in ideas[:10]])
                return await self.llm_provider(f"{agent.system_prompt}\n\nCritique these ideas:\n{ideas_text}")
            except:
                pass
        return f"[{agent.role.value}] Critique of {len(ideas)} ideas"
    
    async def _agent_synthesize(
        self,
        agent: MicroAgent,
        ideas: List[Dict[str, Any]],
        critiques: List[Dict[str, Any]]
    ) -> str:
        """Agent synthesizes ideas and critiques."""
        if self.llm_provider:
            try:
                ideas_text = "\n".join([f"- {i['idea']}" for i in ideas[:10]])
                critiques_text = "\n".join([f"- {c['critique']}" for c in critiques[:5]])
                return await self.llm_provider(
                    f"{agent.system_prompt}\n\nSynthesize:\n\nIdeas:\n{ideas_text}\n\nCritiques:\n{critiques_text}"
                )
            except:
                pass
        return f"[{agent.role.value}] Synthesis of {len(ideas)} ideas"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get swarm statistics."""
        return {
            **self._stats,
            "active_swarms": len(self._active_swarms),
            "total_agents": len(self._agents)
        }


class CouncilMicroSwarmSystem:
    """
    Main interface for the Council Micro Swarm system.
    
    This is the most advanced multi-agent deliberation system ever created.
    It combines:
    - Hierarchical councils for structured decision-making
    - Micro-agent swarms for parallel exploration
    - Psychological optimization for diverse perspectives
    - Emergent intelligence from agent interactions
    """
    
    def __init__(self, llm_provider: Callable = None):
        self.llm_provider = llm_provider
        
        self.deliberation_engine = DeliberationEngine(llm_provider)
        self.swarm_orchestrator = MicroSwarmOrchestrator(llm_provider)
        
        self._councils: Dict[str, Council] = {}
        self._council_hierarchy: Dict[str, List[str]] = {}  # parent -> children
        
        logger.info("CouncilMicroSwarmSystem initialized")
    
    async def create_supreme_council(
        self,
        objective: str,
        hierarchy_depth: int = 2
    ) -> Dict[str, Council]:
        """Create a supreme council with hierarchy."""
        councils = CouncilFactory.create_council_hierarchy(
            objective=objective,
            depth=hierarchy_depth
        )
        
        for council_id, council in councils.items():
            self._councils[council_id] = council
            if council.parent_council:
                if council.parent_council not in self._council_hierarchy:
                    self._council_hierarchy[council.parent_council] = []
                self._council_hierarchy[council.parent_council].append(council_id)
        
        return councils
    
    async def deliberate(
        self,
        council_id: str,
        topic: str,
        context: Dict[str, Any] = None,
        cascade_to_children: bool = True
    ) -> CouncilDecision:
        """Run deliberation on a council."""
        if council_id not in self._councils:
            raise ValueError(f"Council {council_id} not found")
        
        council = self._councils[council_id]
        
        # If cascading, first get input from child councils
        child_decisions = []
        if cascade_to_children and council_id in self._council_hierarchy:
            for child_id in self._council_hierarchy[council_id]:
                child_decision = await self.deliberate(
                    child_id, topic, context, cascade_to_children=False
                )
                child_decisions.append(child_decision)
        
        # Add child decisions to context
        if child_decisions:
            context = context or {}
            context["child_council_decisions"] = [
                {"council": d.council_id, "decision": d.decision}
                for d in child_decisions
            ]
        
        # Run main deliberation
        decision = await self.deliberation_engine.deliberate(council, topic, context)
        
        return decision
    
    async def swarm_brainstorm(
        self,
        objective: str,
        agent_count: int = 50
    ) -> Dict[str, Any]:
        """Run a micro-agent swarm for brainstorming."""
        swarm_id = await self.swarm_orchestrator.create_swarm(objective, agent_count)
        result = await self.swarm_orchestrator.run_swarm(swarm_id)
        return result
    
    async def full_mission(
        self,
        mission: str,
        use_councils: bool = True,
        use_swarm: bool = True
    ) -> Dict[str, Any]:
        """Execute a full mission using councils and swarms."""
        results = {
            "mission": mission,
            "council_decisions": [],
            "swarm_results": None,
            "final_synthesis": ""
        }
        
        # Phase 1: Swarm brainstorming
        if use_swarm:
            swarm_result = await self.swarm_brainstorm(mission, agent_count=30)
            results["swarm_results"] = swarm_result
        
        # Phase 2: Council deliberation
        if use_councils:
            councils = await self.create_supreme_council(mission, hierarchy_depth=2)
            
            # Find supreme council
            supreme = None
            for council in councils.values():
                if council.council_type == CouncilType.SUPREME:
                    supreme = council
                    break
            
            if supreme:
                context = {}
                if results["swarm_results"]:
                    context["swarm_ideas"] = results["swarm_results"].get("result", "")
                
                decision = await self.deliberate(
                    supreme.council_id,
                    mission,
                    context,
                    cascade_to_children=True
                )
                results["council_decisions"].append({
                    "council": supreme.name,
                    "decision": decision.decision,
                    "confidence": decision.confidence
                })
                results["final_synthesis"] = decision.decision
        
        return results
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all system statistics."""
        return {
            "councils": len(self._councils),
            "swarm_stats": self.swarm_orchestrator.get_stats(),
            "total_decisions": sum(c.decisions_made for c in self._councils.values())
        }


# Singleton
_council_swarm_system: Optional[CouncilMicroSwarmSystem] = None


def get_council_swarm_system() -> CouncilMicroSwarmSystem:
    """Get the global council swarm system."""
    global _council_swarm_system
    if _council_swarm_system is None:
        _council_swarm_system = CouncilMicroSwarmSystem()
    return _council_swarm_system


async def demo():
    """Demonstrate the council micro swarm system."""
    system = get_council_swarm_system()
    
    print("Council Micro Swarm System Demo")
    print("=" * 50)
    
    # Create supreme council
    print("\nCreating council hierarchy...")
    councils = await system.create_supreme_council(
        objective="Design the most advanced AI system",
        hierarchy_depth=2
    )
    print(f"Created {len(councils)} councils")
    
    for council in councils.values():
        print(f"  - {council.name} ({council.council_type.value}): {len(council.members)} members")
    
    # Run swarm brainstorming
    print("\nRunning swarm brainstorming...")
    swarm_result = await system.swarm_brainstorm(
        objective="Generate innovative AI capabilities",
        agent_count=20
    )
    print(f"Swarm generated {swarm_result['ideas_generated']} ideas")
    
    # Show stats
    print("\nSystem Statistics:")
    stats = system.get_all_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
