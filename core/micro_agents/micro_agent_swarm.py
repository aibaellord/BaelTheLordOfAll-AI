"""
BAEL - Micro Agent Swarm System
Creates swarms of specialized micro-agents for parallel problem solving.

Revolutionary concepts:
1. Thousands of lightweight micro-agents
2. Psychological role specialization
3. Emergent collective intelligence
4. Competitive and collaborative dynamics
5. Idea evolution through agent interaction
6. Automatic consensus building
7. Quality amplification through diversity
"""

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import json

logger = logging.getLogger("BAEL.MicroAgents")


class MicroRole(Enum):
    """Specialized roles for micro-agents."""
    IDEATOR = "ideator"
    CRITIC = "critic"
    REFINER = "refiner"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"
    EXPLORER = "explorer"
    OPTIMIZER = "optimizer"
    DEVIL_ADVOCATE = "devil_advocate"
    CHAMPION = "champion"
    MEDIATOR = "mediator"


@dataclass
class MicroAgent:
    """A lightweight micro-agent."""
    agent_id: str
    role: MicroRole
    specialty: str = ""
    
    # Psychological amplifiers
    creativity: float = 0.7
    rigor: float = 0.7
    boldness: float = 0.5
    
    # State
    ideas: List[str] = field(default_factory=list)
    critiques: List[str] = field(default_factory=list)
    votes: Dict[str, float] = field(default_factory=dict)
    
    # Performance
    contributions: int = 0
    accepted_ideas: int = 0
    
    def get_prompt_modifier(self) -> str:
        """Get role-specific prompt modifier."""
        modifiers = {
            MicroRole.IDEATOR: "Generate creative, novel ideas. Think outside the box.",
            MicroRole.CRITIC: "Critically evaluate ideas. Find weaknesses and risks.",
            MicroRole.REFINER: "Take existing ideas and make them better. Polish and improve.",
            MicroRole.SYNTHESIZER: "Combine multiple ideas into coherent wholes.",
            MicroRole.VALIDATOR: "Check ideas for correctness and feasibility.",
            MicroRole.EXPLORER: "Explore unconventional approaches. Go to extremes.",
            MicroRole.OPTIMIZER: "Optimize for efficiency and performance.",
            MicroRole.DEVIL_ADVOCATE: "Challenge everything. Play devil's advocate.",
            MicroRole.CHAMPION: "Advocate strongly for the best ideas.",
            MicroRole.MEDIATOR: "Find common ground between conflicting views."
        }
        return modifiers.get(self.role, "Contribute your perspective.")


@dataclass
class Idea:
    """An idea in the swarm."""
    idea_id: str
    content: str
    creator_id: str
    
    # Evolution
    parent_ids: List[str] = field(default_factory=list)
    child_ids: List[str] = field(default_factory=list)
    version: int = 1
    
    # Evaluation
    votes: Dict[str, float] = field(default_factory=dict)
    critiques: List[str] = field(default_factory=list)
    refinements: List[str] = field(default_factory=list)
    
    # Status
    status: str = "active"  # active, refined, merged, rejected
    
    @property
    def score(self) -> float:
        if not self.votes:
            return 0.0
        return sum(self.votes.values()) / len(self.votes)


@dataclass
class SwarmResult:
    """Result from micro-agent swarm."""
    topic: str
    best_ideas: List[Idea]
    consensus_idea: Optional[str]
    agent_contributions: Dict[str, int]
    total_ideas: int
    total_critiques: int
    rounds: int
    execution_time: float


class MicroAgentSwarm:
    """
    Creates and manages micro-agent swarms.
    """
    
    def __init__(
        self,
        llm_provider: Callable = None,
        default_agent_count: int = 20
    ):
        self.llm_provider = llm_provider
        self.default_count = default_agent_count
        
        self._agents: Dict[str, MicroAgent] = {}
        self._ideas: Dict[str, Idea] = {}
        
        # Role distribution (optimized)
        self._role_distribution = {
            MicroRole.IDEATOR: 0.25,
            MicroRole.CRITIC: 0.15,
            MicroRole.REFINER: 0.15,
            MicroRole.SYNTHESIZER: 0.1,
            MicroRole.VALIDATOR: 0.1,
            MicroRole.EXPLORER: 0.1,
            MicroRole.OPTIMIZER: 0.05,
            MicroRole.DEVIL_ADVOCATE: 0.05,
            MicroRole.CHAMPION: 0.025,
            MicroRole.MEDIATOR: 0.025
        }
        
        logger.info("MicroAgentSwarm initialized")
    
    async def create_swarm(
        self,
        topic: str,
        agent_count: int = None,
        specialties: List[str] = None
    ) -> List[MicroAgent]:
        """Create a swarm of micro-agents for a topic."""
        count = agent_count or self.default_count
        agents = []
        
        # Distribute roles
        for role, ratio in self._role_distribution.items():
            role_count = max(1, int(count * ratio))
            for i in range(role_count):
                agent = MicroAgent(
                    agent_id=f"micro_{role.value}_{i}_{hashlib.md5(f'{topic}{i}'.encode()).hexdigest()[:6]}",
                    role=role,
                    specialty=random.choice(specialties) if specialties else "",
                    creativity=0.5 + random.random() * 0.5,
                    rigor=0.5 + random.random() * 0.5,
                    boldness=0.3 + random.random() * 0.7
                )
                agents.append(agent)
                self._agents[agent.agent_id] = agent
                
                if len(agents) >= count:
                    break
            if len(agents) >= count:
                break
        
        logger.info(f"Created swarm of {len(agents)} micro-agents")
        return agents
    
    async def run_ideation(
        self,
        topic: str,
        agents: List[MicroAgent],
        rounds: int = 3
    ) -> SwarmResult:
        """Run ideation process with micro-agents."""
        import time
        start_time = time.time()
        
        all_ideas = []
        all_critiques = []
        
        for round_num in range(rounds):
            # Phase 1: Generate ideas
            for agent in agents:
                if agent.role in [MicroRole.IDEATOR, MicroRole.EXPLORER]:
                    idea = await self._generate_idea(agent, topic, all_ideas)
                    if idea:
                        all_ideas.append(idea)
                        agent.contributions += 1
            
            # Phase 2: Critique ideas
            for agent in agents:
                if agent.role in [MicroRole.CRITIC, MicroRole.DEVIL_ADVOCATE, MicroRole.VALIDATOR]:
                    for idea in all_ideas[-5:]:  # Critique recent ideas
                        critique = await self._critique_idea(agent, idea)
                        if critique:
                            all_critiques.append(critique)
                            idea.critiques.append(critique)
            
            # Phase 3: Refine ideas
            for agent in agents:
                if agent.role in [MicroRole.REFINER, MicroRole.OPTIMIZER]:
                    for idea in all_ideas:
                        if idea.score >= 0.5:
                            refined = await self._refine_idea(agent, idea)
                            if refined:
                                all_ideas.append(refined)
            
            # Phase 4: Vote on ideas
            for agent in agents:
                for idea in all_ideas:
                    vote = self._vote_on_idea(agent, idea)
                    idea.votes[agent.agent_id] = vote
            
            # Phase 5: Synthesize (last round)
            if round_num == rounds - 1:
                for agent in agents:
                    if agent.role == MicroRole.SYNTHESIZER:
                        top_ideas = sorted(all_ideas, key=lambda i: i.score, reverse=True)[:5]
                        synthesis = await self._synthesize_ideas(agent, top_ideas)
                        if synthesis:
                            all_ideas.append(synthesis)
        
        # Build result
        sorted_ideas = sorted(all_ideas, key=lambda i: i.score, reverse=True)
        
        contributions = {}
        for agent in agents:
            contributions[agent.agent_id] = agent.contributions
        
        # Find consensus
        consensus = None
        if sorted_ideas:
            top_idea = sorted_ideas[0]
            if top_idea.score >= 0.7:
                consensus = top_idea.content
        
        return SwarmResult(
            topic=topic,
            best_ideas=sorted_ideas[:10],
            consensus_idea=consensus,
            agent_contributions=contributions,
            total_ideas=len(all_ideas),
            total_critiques=len(all_critiques),
            rounds=rounds,
            execution_time=time.time() - start_time
        )
    
    async def _generate_idea(
        self,
        agent: MicroAgent,
        topic: str,
        existing_ideas: List[Idea]
    ) -> Optional[Idea]:
        """Generate a new idea."""
        prompt = f"""
{agent.get_prompt_modifier()}

Topic: {topic}

Existing ideas to build on or differentiate from:
{json.dumps([i.content[:100] for i in existing_ideas[-5:]], indent=2) if existing_ideas else "None yet"}

Generate ONE innovative idea. Be concise but impactful.
"""
        
        if self.llm_provider:
            content = await self.llm_provider(prompt)
        else:
            content = f"[{agent.role.value}] Idea for: {topic}"
        
        idea = Idea(
            idea_id=f"idea_{hashlib.md5(f'{content[:50]}{datetime.utcnow()}'.encode()).hexdigest()[:10]}",
            content=content,
            creator_id=agent.agent_id
        )
        
        self._ideas[idea.idea_id] = idea
        agent.ideas.append(idea.idea_id)
        
        return idea
    
    async def _critique_idea(
        self,
        agent: MicroAgent,
        idea: Idea
    ) -> Optional[str]:
        """Critique an idea."""
        prompt = f"""
{agent.get_prompt_modifier()}

Idea to critique:
{idea.content}

Provide constructive criticism. Be specific about weaknesses and improvements.
"""
        
        if self.llm_provider:
            critique = await self.llm_provider(prompt)
        else:
            critique = f"[{agent.role.value}] Critique: Consider improvements"
        
        agent.critiques.append(critique)
        return critique
    
    async def _refine_idea(
        self,
        agent: MicroAgent,
        idea: Idea
    ) -> Optional[Idea]:
        """Refine an existing idea."""
        prompt = f"""
{agent.get_prompt_modifier()}

Original idea:
{idea.content}

Critiques received:
{json.dumps(idea.critiques[-3:], indent=2) if idea.critiques else "None"}

Create an improved version that addresses the critiques.
"""
        
        if self.llm_provider:
            content = await self.llm_provider(prompt)
        else:
            content = f"[Refined] {idea.content}"
        
        refined = Idea(
            idea_id=f"idea_{hashlib.md5(f'{content[:50]}{datetime.utcnow()}'.encode()).hexdigest()[:10]}",
            content=content,
            creator_id=agent.agent_id,
            parent_ids=[idea.idea_id],
            version=idea.version + 1
        )
        
        idea.child_ids.append(refined.idea_id)
        idea.status = "refined"
        
        self._ideas[refined.idea_id] = refined
        agent.contributions += 1
        
        return refined
    
    async def _synthesize_ideas(
        self,
        agent: MicroAgent,
        ideas: List[Idea]
    ) -> Optional[Idea]:
        """Synthesize multiple ideas into one."""
        prompt = f"""
{agent.get_prompt_modifier()}

Ideas to synthesize:
{json.dumps([i.content for i in ideas], indent=2)}

Create a synthesis that combines the best elements of all ideas.
"""
        
        if self.llm_provider:
            content = await self.llm_provider(prompt)
        else:
            content = f"[Synthesis] Combined insights from {len(ideas)} ideas"
        
        synthesis = Idea(
            idea_id=f"idea_synth_{hashlib.md5(f'{content[:50]}{datetime.utcnow()}'.encode()).hexdigest()[:10]}",
            content=content,
            creator_id=agent.agent_id,
            parent_ids=[i.idea_id for i in ideas],
            version=max(i.version for i in ideas) + 1
        )
        
        self._ideas[synthesis.idea_id] = synthesis
        agent.contributions += 1
        
        return synthesis
    
    def _vote_on_idea(self, agent: MicroAgent, idea: Idea) -> float:
        """Agent votes on an idea (0-1 score)."""
        # Base score on role perspective
        base_score = 0.5
        
        if agent.role == MicroRole.CRITIC:
            # Critics are more harsh
            base_score = 0.4
        elif agent.role == MicroRole.CHAMPION:
            # Champions are more generous
            base_score = 0.6
        
        # Add randomness for diversity
        vote = base_score + (random.random() - 0.5) * 0.4
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, vote))


# Global instance
_micro_swarm: Optional[MicroAgentSwarm] = None


def get_micro_swarm() -> MicroAgentSwarm:
    """Get the global micro-agent swarm."""
    global _micro_swarm
    if _micro_swarm is None:
        _micro_swarm = MicroAgentSwarm()
    return _micro_swarm
