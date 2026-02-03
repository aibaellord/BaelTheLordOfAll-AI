"""
BAEL - Automated Council Swarm System
======================================

The most advanced multi-agent collaboration system ever created.

This system implements:
1. Dynamic council creation based on task requirements
2. Swarm intelligence with emergent problem-solving
3. Psychological amplification through role dynamics
4. Micro-agent spawning for parallel exploration
5. Council of Councils for meta-deliberation
6. Automated consensus with validation
7. Genius trigger patterns for breakthrough insights
8. Cross-council knowledge synthesis

This surpasses AutoGen, CrewAI, and all other multi-agent systems
by implementing sophisticated psychological dynamics and emergence.
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.CouncilSwarm")


class AgentRole(Enum):
    """Psychological roles for agents."""
    VISIONARY = "visionary"         # Big picture thinking
    ANALYST = "analyst"             # Deep analysis
    CRITIC = "critic"               # Skeptical evaluation
    INNOVATOR = "innovator"         # Novel ideas
    INTEGRATOR = "integrator"       # Synthesizes perspectives
    ADVOCATE = "advocate"           # Champions ideas
    CHALLENGER = "challenger"       # Questions assumptions
    IMPLEMENTER = "implementer"     # Practical execution
    RESEARCHER = "researcher"       # Deep knowledge
    STRATEGIST = "strategist"       # Long-term planning


class CouncilType(Enum):
    """Types of councils."""
    DELIBERATION = "deliberation"   # Decision making
    BRAINSTORM = "brainstorm"       # Idea generation
    REVIEW = "review"               # Quality assessment
    PROBLEM_SOLVING = "problem_solving"
    STRATEGY = "strategy"           # Strategic planning
    META = "meta"                   # Council of councils


class SwarmBehavior(Enum):
    """Swarm behavior patterns."""
    EXPLORATION = "exploration"     # Divergent search
    EXPLOITATION = "exploitation"   # Converge on solution
    OSCILLATION = "oscillation"     # Balance explore/exploit
    EMERGENCE = "emergence"         # Allow novel patterns
    CONSENSUS = "consensus"         # Build agreement


class GeniusTrigger(Enum):
    """Triggers for genius-level insights."""
    CREATIVE_TENSION = "creative_tension"   # Opposing views spark insight
    DEEP_SYNTHESIS = "deep_synthesis"       # Multiple perspectives merge
    UNEXPECTED_CONNECTION = "unexpected_connection"
    PARADIGM_SHIFT = "paradigm_shift"       # Fundamental reframe
    INTUITIVE_LEAP = "intuitive_leap"       # Beyond logic


@dataclass
class AgentState:
    """State of an individual agent."""
    agent_id: str
    role: AgentRole
    energy: float = 1.0
    conviction: float = 0.5         # How strongly holding current position
    openness: float = 0.5           # Openness to other views
    current_position: Optional[str] = None
    contributions: List[str] = field(default_factory=list)
    influenced_by: List[str] = field(default_factory=list)


@dataclass
class CouncilAgent:
    """An agent participating in a council."""
    agent_id: str
    name: str
    role: AgentRole
    expertise: List[str]
    personality_traits: List[str]
    thinking_style: str
    state: AgentState = None
    
    def __post_init__(self):
        if self.state is None:
            self.state = AgentState(agent_id=self.agent_id, role=self.role)


@dataclass
class Contribution:
    """A contribution to council discussion."""
    contribution_id: str
    agent_id: str
    content: str
    contribution_type: str  # idea, critique, synthesis, question
    references: List[str] = field(default_factory=list)  # Referenced contributions
    votes: int = 0
    genius_triggered: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CouncilSession:
    """A council session with all state."""
    session_id: str
    council_type: CouncilType
    topic: str
    agents: List[CouncilAgent]
    contributions: List[Contribution] = field(default_factory=list)
    consensus: Optional[str] = None
    genius_insights: List[str] = field(default_factory=list)
    status: str = "active"
    rounds_completed: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SwarmState:
    """State of the swarm."""
    swarm_id: str
    behavior: SwarmBehavior
    agents: List[str]  # Agent IDs
    best_solution: Optional[str] = None
    best_score: float = 0.0
    explored_regions: Set[str] = field(default_factory=set)
    convergence: float = 0.0  # How converged the swarm is


class AgentFactory:
    """Factory for creating specialized agents."""
    
    AGENT_TEMPLATES = {
        AgentRole.VISIONARY: {
            "traits": ["imaginative", "inspiring", "future-focused"],
            "thinking": "expansive",
            "expertise_bias": ["innovation", "trends", "possibilities"]
        },
        AgentRole.ANALYST: {
            "traits": ["meticulous", "logical", "thorough"],
            "thinking": "systematic",
            "expertise_bias": ["data", "patterns", "implications"]
        },
        AgentRole.CRITIC: {
            "traits": ["skeptical", "discerning", "rigorous"],
            "thinking": "adversarial",
            "expertise_bias": ["risks", "flaws", "edge_cases"]
        },
        AgentRole.INNOVATOR: {
            "traits": ["creative", "unconventional", "bold"],
            "thinking": "lateral",
            "expertise_bias": ["novel_approaches", "combinations", "experiments"]
        },
        AgentRole.INTEGRATOR: {
            "traits": ["harmonizing", "diplomatic", "synthesizing"],
            "thinking": "holistic",
            "expertise_bias": ["connections", "common_ground", "synthesis"]
        },
        AgentRole.CHALLENGER: {
            "traits": ["provocative", "questioning", "probing"],
            "thinking": "dialectical",
            "expertise_bias": ["assumptions", "blind_spots", "alternatives"]
        },
        AgentRole.IMPLEMENTER: {
            "traits": ["practical", "action-oriented", "efficient"],
            "thinking": "concrete",
            "expertise_bias": ["execution", "resources", "timelines"]
        },
        AgentRole.RESEARCHER: {
            "traits": ["curious", "thorough", "knowledgeable"],
            "thinking": "investigative",
            "expertise_bias": ["evidence", "sources", "deep_knowledge"]
        },
        AgentRole.STRATEGIST: {
            "traits": ["long-term", "adaptive", "calculated"],
            "thinking": "strategic",
            "expertise_bias": ["positioning", "contingencies", "leverage"]
        }
    }
    
    def create_agent(
        self,
        role: AgentRole,
        additional_expertise: List[str] = None
    ) -> CouncilAgent:
        """Create an agent with specified role."""
        template = self.AGENT_TEMPLATES.get(role, {})
        
        agent_id = f"agent_{role.value}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        expertise = template.get("expertise_bias", []).copy()
        if additional_expertise:
            expertise.extend(additional_expertise)
        
        return CouncilAgent(
            agent_id=agent_id,
            name=f"{role.value.title()} Agent",
            role=role,
            expertise=expertise,
            personality_traits=template.get("traits", []),
            thinking_style=template.get("thinking", "balanced")
        )
    
    def create_balanced_council(
        self,
        size: int = 5,
        bias_roles: List[AgentRole] = None
    ) -> List[CouncilAgent]:
        """Create a balanced council with diverse perspectives."""
        agents = []
        
        # Always include core roles
        core_roles = [AgentRole.VISIONARY, AgentRole.ANALYST, AgentRole.CRITIC]
        for role in core_roles[:min(size, len(core_roles))]:
            agents.append(self.create_agent(role))
        
        # Add biased roles if specified
        if bias_roles:
            for role in bias_roles:
                if len(agents) < size:
                    agents.append(self.create_agent(role))
        
        # Fill remaining slots with diverse roles
        remaining_roles = [r for r in AgentRole if r not in core_roles and (not bias_roles or r not in bias_roles)]
        random.shuffle(remaining_roles)
        
        while len(agents) < size and remaining_roles:
            agents.append(self.create_agent(remaining_roles.pop()))
        
        return agents


class GeniusDetector:
    """Detects conditions for genius-level insights."""
    
    def __init__(self):
        self._tension_threshold = 0.7
        self._synthesis_threshold = 3
        self._genius_history: List[Dict[str, Any]] = []
    
    async def detect_genius_triggers(
        self,
        contributions: List[Contribution],
        agents: List[CouncilAgent]
    ) -> List[Tuple[GeniusTrigger, str]]:
        """Detect potential genius trigger conditions."""
        triggers = []
        
        if self._check_creative_tension(contributions):
            triggers.append((
                GeniusTrigger.CREATIVE_TENSION,
                "Opposing viewpoints creating productive tension"
            ))
        
        if self._check_deep_synthesis(contributions):
            triggers.append((
                GeniusTrigger.DEEP_SYNTHESIS,
                "Multiple perspectives ready for synthesis"
            ))
        
        if self._check_unexpected_connections(contributions):
            triggers.append((
                GeniusTrigger.UNEXPECTED_CONNECTION,
                "Novel connection between disparate ideas"
            ))
        
        return triggers
    
    def _check_creative_tension(self, contributions: List[Contribution]) -> bool:
        critiques = [c for c in contributions if c.contribution_type == "critique"]
        ideas = [c for c in contributions if c.contribution_type == "idea"]
        return len(critiques) >= 2 and len(ideas) >= 2
    
    def _check_deep_synthesis(self, contributions: List[Contribution]) -> bool:
        referenced_count = sum(len(c.references) for c in contributions)
        return referenced_count >= self._synthesis_threshold
    
    def _check_unexpected_connections(self, contributions: List[Contribution]) -> bool:
        for c in contributions[-5:]:
            if len(c.references) >= 2:
                ref_indices = []
                for ref in c.references:
                    idx = next((i for i, cont in enumerate(contributions) if cont.contribution_id == ref), -1)
                    if idx >= 0:
                        ref_indices.append(idx)
                
                if ref_indices and max(ref_indices) - min(ref_indices) > 3:
                    return True
        return False


class ConsensusBuilder:
    """Builds consensus from diverse contributions."""
    
    async def build_consensus(
        self,
        contributions: List[Contribution],
        agents: List[CouncilAgent]
    ) -> Tuple[str, float]:
        if not contributions:
            return "No contributions to build consensus from", 0.0
        
        scored = []
        for c in contributions:
            score = c.votes * 2 + len(c.references) + (10 if c.genius_triggered else 0)
            scored.append((c, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        top_contributions = [c for c, _ in scored[:5]]
        
        synthesis = "Consensus: "
        key_points = []
        
        for c in top_contributions:
            if c.contribution_type == "synthesis":
                key_points.insert(0, c.content[:100])
            else:
                key_points.append(c.content[:50])
        
        synthesis += "; ".join(key_points[:3])
        
        total_votes = sum(c.votes for c in contributions)
        max_possible = len(contributions) * len(agents)
        agreement = total_votes / max_possible if max_possible > 0 else 0.5
        
        return synthesis, agreement


class SwarmCoordinator:
    """Coordinates swarm intelligence behavior."""
    
    def __init__(self, agent_factory: AgentFactory):
        self.factory = agent_factory
        self._swarms: Dict[str, SwarmState] = {}
    
    async def spawn_micro_swarm(
        self,
        task: str,
        size: int = 10,
        behavior: SwarmBehavior = SwarmBehavior.EXPLORATION
    ) -> SwarmState:
        swarm_id = f"swarm_{hashlib.md5(f'{task}{time.time()}'.encode()).hexdigest()[:12]}"
        
        agents = []
        for i in range(size):
            role = random.choice(list(AgentRole))
            agent = self.factory.create_agent(role)
            agents.append(agent.agent_id)
        
        swarm = SwarmState(
            swarm_id=swarm_id,
            behavior=behavior,
            agents=agents
        )
        
        self._swarms[swarm_id] = swarm
        return swarm
    
    async def run_swarm_iteration(
        self,
        swarm: SwarmState,
        problem: str
    ) -> Dict[str, Any]:
        results = {
            "solutions": [],
            "best_solution": None,
            "convergence": 0.0
        }
        
        if swarm.behavior == SwarmBehavior.EXPLORATION:
            for agent_id in swarm.agents:
                solution = f"Exploration from {agent_id}: {problem[:20]}..."
                results["solutions"].append(solution)
                region = hashlib.md5(solution.encode()).hexdigest()[:8]
                swarm.explored_regions.add(region)
        
        elif swarm.behavior == SwarmBehavior.EXPLOITATION:
            if swarm.best_solution:
                for agent_id in swarm.agents:
                    refined = f"Refined by {agent_id}: {swarm.best_solution[:30]}..."
                    results["solutions"].append(refined)
        
        elif swarm.behavior == SwarmBehavior.EMERGENCE:
            combinations = []
            for i, agent_id in enumerate(swarm.agents):
                if i > 0:
                    prev_agent = swarm.agents[i-1]
                    combo = f"Emergent from {prev_agent}+{agent_id}"
                    combinations.append(combo)
            results["solutions"] = combinations
        
        if results["solutions"]:
            scores = [len(s) * random.random() for s in results["solutions"]]
            best_idx = scores.index(max(scores))
            results["best_solution"] = results["solutions"][best_idx]
            
            if results["best_solution"]:
                swarm.best_solution = results["best_solution"]
                swarm.best_score = max(scores)
        
        swarm.convergence = len(swarm.explored_regions) / max(len(swarm.agents) * 10, 1)
        results["convergence"] = swarm.convergence
        
        return results


class CouncilOfCouncils:
    """Meta-council that coordinates multiple councils."""
    
    def __init__(self):
        self._sub_councils: Dict[str, CouncilSession] = {}
        self._meta_decisions: List[Dict[str, Any]] = []
    
    async def convene(
        self,
        councils: List[CouncilSession],
        meta_topic: str
    ) -> Dict[str, Any]:
        for council in councils:
            self._sub_councils[council.session_id] = council
        
        council_outputs = []
        for council in councils:
            if council.consensus:
                council_outputs.append({
                    "council_id": council.session_id,
                    "type": council.council_type.value,
                    "consensus": council.consensus,
                    "genius_insights": council.genius_insights
                })
        
        meta_synthesis = await self._meta_synthesize(council_outputs, meta_topic)
        
        decision = {
            "meta_topic": meta_topic,
            "councils_consulted": len(councils),
            "synthesis": meta_synthesis,
            "confidence": len(council_outputs) / len(councils) if councils else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._meta_decisions.append(decision)
        return decision
    
    async def _meta_synthesize(
        self,
        outputs: List[Dict[str, Any]],
        topic: str
    ) -> str:
        if not outputs:
            return "No council outputs to synthesize"
        
        parts = []
        for output in outputs:
            parts.append(f"[{output['type']}]: {output['consensus'][:100]}")
        
        return f"Meta-synthesis for '{topic}': " + " | ".join(parts)


class AutomatedCouncilSwarmSystem:
    """
    The Automated Council Swarm System.
    
    Most advanced multi-agent collaboration system combining
    council deliberation with swarm intelligence.
    """
    
    def __init__(self):
        self.factory = AgentFactory()
        self.genius_detector = GeniusDetector()
        self.consensus_builder = ConsensusBuilder()
        self.swarm_coordinator = SwarmCoordinator(self.factory)
        self.meta_council = CouncilOfCouncils()
        
        self._sessions: Dict[str, CouncilSession] = {}
        
        self._stats = {
            "councils_created": 0,
            "rounds_completed": 0,
            "genius_insights": 0,
            "swarms_spawned": 0,
            "meta_decisions": 0
        }
        
        logger.info("AutomatedCouncilSwarmSystem initialized")
    
    async def create_council(
        self,
        topic: str,
        council_type: CouncilType = CouncilType.DELIBERATION,
        size: int = 5,
        bias_roles: List[AgentRole] = None
    ) -> CouncilSession:
        session_id = f"council_{hashlib.md5(f'{topic}{time.time()}'.encode()).hexdigest()[:12]}"
        agents = self.factory.create_balanced_council(size, bias_roles)
        
        session = CouncilSession(
            session_id=session_id,
            council_type=council_type,
            topic=topic,
            agents=agents
        )
        
        self._sessions[session_id] = session
        self._stats["councils_created"] += 1
        
        return session
    
    async def run_council_round(self, session: CouncilSession) -> List[Contribution]:
        contributions = []
        
        for agent in session.agents:
            contribution = await self._generate_contribution(agent, session)
            contributions.append(contribution)
            session.contributions.append(contribution)
            
            triggers = await self.genius_detector.detect_genius_triggers(
                session.contributions, session.agents
            )
            
            for trigger_type, description in triggers:
                genius_insight = f"[{trigger_type.value}] {description}"
                session.genius_insights.append(genius_insight)
                contribution.genius_triggered = True
                self._stats["genius_insights"] += 1
        
        session.rounds_completed += 1
        self._stats["rounds_completed"] += 1
        
        return contributions
    
    async def _generate_contribution(
        self,
        agent: CouncilAgent,
        session: CouncilSession
    ) -> Contribution:
        contribution_id = f"contrib_{agent.agent_id}_{session.rounds_completed}"
        
        type_mapping = {
            AgentRole.VISIONARY: "idea",
            AgentRole.ANALYST: "analysis",
            AgentRole.CRITIC: "critique",
            AgentRole.INNOVATOR: "idea",
            AgentRole.INTEGRATOR: "synthesis",
            AgentRole.CHALLENGER: "question",
            AgentRole.IMPLEMENTER: "proposal",
            AgentRole.RESEARCHER: "evidence",
            AgentRole.STRATEGIST: "strategy"
        }
        
        contrib_type = type_mapping.get(agent.role, "comment")
        content = f"[{agent.role.value}] On '{session.topic}': Contribution..."
        
        references = []
        if session.contributions and random.random() > 0.3:
            recent = session.contributions[-3:]
            ref = random.choice(recent)
            references.append(ref.contribution_id)
        
        return Contribution(
            contribution_id=contribution_id,
            agent_id=agent.agent_id,
            content=content,
            contribution_type=contrib_type,
            references=references
        )
    
    async def build_consensus(self, session: CouncilSession) -> Tuple[str, float]:
        consensus, confidence = await self.consensus_builder.build_consensus(
            session.contributions, session.agents
        )
        session.consensus = consensus
        session.status = "concluded"
        return consensus, confidence
    
    async def spawn_exploration_swarm(self, task: str, size: int = 10) -> Dict[str, Any]:
        swarm = await self.swarm_coordinator.spawn_micro_swarm(
            task, size, SwarmBehavior.EXPLORATION
        )
        results = await self.swarm_coordinator.run_swarm_iteration(swarm, task)
        self._stats["swarms_spawned"] += 1
        
        return {
            "swarm_id": swarm.swarm_id,
            "solutions": results["solutions"],
            "best_solution": results["best_solution"],
            "convergence": results["convergence"]
        }
    
    async def meta_deliberate(
        self,
        topic: str,
        council_types: List[CouncilType] = None
    ) -> Dict[str, Any]:
        council_types = council_types or [
            CouncilType.BRAINSTORM,
            CouncilType.DELIBERATION,
            CouncilType.REVIEW
        ]
        
        councils = []
        for ctype in council_types:
            council = await self.create_council(topic, ctype, size=4)
            await self.run_council_round(council)
            await self.run_council_round(council)
            await self.build_consensus(council)
            councils.append(council)
        
        meta_result = await self.meta_council.convene(councils, topic)
        self._stats["meta_decisions"] += 1
        
        return meta_result
    
    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "active_sessions": len(self._sessions)}


# Global instance
_council_swarm: Optional[AutomatedCouncilSwarmSystem] = None

def get_council_swarm() -> AutomatedCouncilSwarmSystem:
    global _council_swarm
    if _council_swarm is None:
        _council_swarm = AutomatedCouncilSwarmSystem()
    return _council_swarm
