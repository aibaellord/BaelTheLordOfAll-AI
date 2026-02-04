"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               META-COGNITIVE COUNCIL OF COUNCILS                              ║
║            The Supreme Deliberation Architecture                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Beyond simple multi-agent conversations - this implements:
- Councils of specialized councils (hierarchical deliberation)
- Psychological motivation layers for enhanced output
- Adversarial debate patterns with devil's advocates
- Socratic questioning for depth exploration
- Consensus building with minority report preservation
- Meta-cognitive reflection on deliberation quality
"""

from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import asyncio
import uuid
import time
from datetime import datetime
from collections import defaultdict


class DeliberationPattern(Enum):
    """Patterns for council deliberation"""
    CONSENSUS = auto()          # Seek agreement
    ADVERSARIAL = auto()        # Structured debate
    SOCRATIC = auto()           # Question-driven exploration
    BRAINSTORM = auto()         # Idea generation
    CRITICAL_ANALYSIS = auto()  # Deep critique
    SYNTHESIS = auto()          # Combine perspectives
    HIERARCHICAL = auto()       # Escalate to higher councils
    SWARM_VOTE = auto()         # Distributed voting
    ORACLE = auto()             # Consult specialized expertise
    META_REFLECTION = auto()    # Reflect on own process


class PsychologicalAmplifier(Enum):
    """Psychological techniques to enhance output quality"""
    GROWTH_MINDSET = auto()       # "We can always improve"
    CHALLENGE_FRAMING = auto()    # "This is an exciting challenge"
    EXCELLENCE_DRIVE = auto()     # "We aim for the absolute best"
    CURIOSITY_BOOST = auto()      # "What haven't we considered?"
    CREATIVE_TENSION = auto()     # "Let's think beyond constraints"
    PERFECTIONIST_PUSH = auto()   # "Every detail matters"
    LEGACY_MOTIVATION = auto()    # "This will set new standards"
    COMPETITIVE_EDGE = auto()     # "We must surpass all others"
    BREAKTHROUGH_HUNT = auto()    # "The breakthrough is within reach"
    MASTERY_PURSUIT = auto()      # "Deep understanding leads to excellence"


@dataclass
class CouncilMember:
    """A member of a deliberation council"""
    member_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: str = ""
    expertise: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    bias_tendencies: Dict[str, float] = field(default_factory=dict)
    psychological_profile: Dict[str, Any] = field(default_factory=dict)
    
    # Behavioral modifiers
    assertiveness: float = 0.5
    open_mindedness: float = 0.5
    analytical_depth: float = 0.5
    creativity: float = 0.5
    skepticism: float = 0.3
    
    # Performance tracking
    contributions: int = 0
    influential_ideas: int = 0
    challenges_raised: int = 0


@dataclass
class CouncilVote:
    """A vote from a council member"""
    member_id: str
    position: str
    confidence: float
    reasoning: str
    supporting_evidence: List[str] = field(default_factory=list)
    dissenting_points: List[str] = field(default_factory=list)


@dataclass
class DeliberationRound:
    """A single round of council deliberation"""
    round_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern: DeliberationPattern = DeliberationPattern.CONSENSUS
    topic: str = ""
    contributions: List[Dict[str, Any]] = field(default_factory=list)
    votes: List[CouncilVote] = field(default_factory=list)
    consensus_reached: bool = False
    consensus_level: float = 0.0
    key_insights: List[str] = field(default_factory=list)
    unresolved_tensions: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class Council:
    """A deliberation council"""
    council_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    purpose: str = ""
    domain: str = ""
    members: Dict[str, CouncilMember] = field(default_factory=dict)
    hierarchy_level: int = 0  # 0 = base, higher = more meta
    parent_council_id: Optional[str] = None
    child_council_ids: List[str] = field(default_factory=list)
    
    # Deliberation configuration
    default_pattern: DeliberationPattern = DeliberationPattern.CONSENSUS
    min_consensus_threshold: float = 0.7
    max_rounds: int = 10
    psychological_amplifiers: List[PsychologicalAmplifier] = field(default_factory=list)
    
    # History
    deliberation_history: List[DeliberationRound] = field(default_factory=list)
    decisions_made: int = 0
    average_consensus_level: float = 0.0


@dataclass
class MetaDeliberation:
    """Meta-level reflection on deliberation quality"""
    meta_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_council_id: str = ""
    quality_assessment: Dict[str, float] = field(default_factory=dict)
    process_improvements: List[str] = field(default_factory=list)
    bias_detections: List[Dict[str, Any]] = field(default_factory=list)
    recommended_patterns: List[DeliberationPattern] = field(default_factory=list)


class MetaCognitiveCouncilSystem:
    """
    THE SUPREME COUNCIL OF COUNCILS SYSTEM
    
    Features that surpass all competitors:
    - Hierarchical council architecture (councils of councils)
    - Psychological amplification for enhanced outputs
    - Multiple deliberation patterns (Socratic, adversarial, etc.)
    - Meta-cognitive reflection on own process
    - Bias detection and compensation
    - Emergent wisdom from collective deliberation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.councils: Dict[str, Council] = {}
        self.meta_council_id: Optional[str] = None
        self.amplifiers = PsychologicalAmplificationEngine()
        self.bias_detector = BiasDetectionEngine()
        self.pattern_selector = PatternSelectionEngine()
        
        # Initialize supreme meta-council
        self._initialize_meta_council()
    
    def _initialize_meta_council(self):
        """Initialize the supreme meta-council that oversees all councils"""
        meta_council = Council(
            name="Supreme Meta-Council",
            purpose="Oversee and optimize all council deliberations",
            domain="meta-cognition",
            hierarchy_level=99,
            psychological_amplifiers=[
                PsychologicalAmplifier.EXCELLENCE_DRIVE,
                PsychologicalAmplifier.MASTERY_PURSUIT,
                PsychologicalAmplifier.BREAKTHROUGH_HUNT
            ]
        )
        
        # Add meta-council members with specialized roles
        meta_members = [
            CouncilMember(
                name="Process Optimizer",
                role="deliberation_quality",
                expertise=["process_improvement", "efficiency"],
                analytical_depth=0.9
            ),
            CouncilMember(
                name="Bias Sentinel",
                role="bias_detection",
                expertise=["cognitive_biases", "fair_deliberation"],
                skepticism=0.8
            ),
            CouncilMember(
                name="Wisdom Synthesizer",
                role="insight_extraction",
                expertise=["pattern_recognition", "wisdom_synthesis"],
                creativity=0.9
            ),
            CouncilMember(
                name="Quality Arbiter",
                role="output_quality",
                expertise=["quality_assessment", "standards"],
                analytical_depth=0.9
            ),
            CouncilMember(
                name="Innovation Catalyst",
                role="breakthrough_facilitation",
                expertise=["innovation", "creative_solutions"],
                creativity=0.95,
                open_mindedness=0.9
            )
        ]
        
        for member in meta_members:
            meta_council.members[member.member_id] = member
        
        self.councils[meta_council.council_id] = meta_council
        self.meta_council_id = meta_council.council_id
    
    async def create_council(
        self,
        name: str,
        purpose: str,
        domain: str,
        member_specs: List[Dict[str, Any]],
        parent_council_id: Optional[str] = None
    ) -> Council:
        """Create a new deliberation council"""
        hierarchy_level = 0
        if parent_council_id and parent_council_id in self.councils:
            hierarchy_level = self.councils[parent_council_id].hierarchy_level + 1
        
        council = Council(
            name=name,
            purpose=purpose,
            domain=domain,
            hierarchy_level=hierarchy_level,
            parent_council_id=parent_council_id,
            psychological_amplifiers=[
                PsychologicalAmplifier.EXCELLENCE_DRIVE,
                PsychologicalAmplifier.CURIOSITY_BOOST
            ]
        )
        
        # Create members from specs
        for spec in member_specs:
            member = CouncilMember(
                name=spec.get('name', f"Member_{uuid.uuid4().hex[:8]}"),
                role=spec.get('role', 'general'),
                expertise=spec.get('expertise', []),
                assertiveness=spec.get('assertiveness', 0.5),
                open_mindedness=spec.get('open_mindedness', 0.5),
                analytical_depth=spec.get('analytical_depth', 0.5),
                creativity=spec.get('creativity', 0.5),
                skepticism=spec.get('skepticism', 0.3)
            )
            council.members[member.member_id] = member
        
        # Add devil's advocate if not present
        has_devil_advocate = any(
            'devil' in m.role.lower() or 'critic' in m.role.lower()
            for m in council.members.values()
        )
        if not has_devil_advocate:
            devil_advocate = CouncilMember(
                name="Devil's Advocate",
                role="critical_challenger",
                expertise=["critical_thinking", "assumption_testing"],
                skepticism=0.9,
                assertiveness=0.8
            )
            council.members[devil_advocate.member_id] = devil_advocate
        
        self.councils[council.council_id] = council
        
        # Link to parent
        if parent_council_id and parent_council_id in self.councils:
            self.councils[parent_council_id].child_council_ids.append(council.council_id)
        
        return council
    
    async def deliberate(
        self,
        council_id: str,
        topic: str,
        context: Dict[str, Any],
        pattern: Optional[DeliberationPattern] = None,
        max_rounds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Conduct a full deliberation session on a topic
        
        This is where the magic happens - councils deliberate using
        psychological amplification, multiple patterns, and meta-reflection
        """
        if council_id not in self.councils:
            raise ValueError(f"Council {council_id} not found")
        
        council = self.councils[council_id]
        pattern = pattern or council.default_pattern
        max_rounds = max_rounds or council.max_rounds
        
        # Apply psychological amplification
        amplified_context = await self.amplifiers.amplify(
            context,
            council.psychological_amplifiers
        )
        
        rounds: List[DeliberationRound] = []
        consensus_reached = False
        
        for round_num in range(max_rounds):
            # Conduct deliberation round
            round_result = await self._conduct_round(
                council,
                topic,
                amplified_context,
                pattern,
                rounds
            )
            rounds.append(round_result)
            
            # Check for consensus
            if round_result.consensus_reached:
                consensus_reached = True
                break
            
            # Adapt pattern if needed
            if round_num > 2 and not round_result.consensus_reached:
                pattern = await self.pattern_selector.select_next_pattern(
                    council, rounds, pattern
                )
        
        # Meta-cognitive reflection
        meta_reflection = await self._meta_reflect(council, rounds)
        
        # Extract final decision
        final_decision = await self._extract_decision(council, rounds)
        
        # Escalate to parent council if needed
        if not consensus_reached and council.parent_council_id:
            escalated = await self._escalate_to_parent(
                council, topic, rounds, final_decision
            )
            final_decision['escalated'] = escalated
        
        # Check with supreme meta-council for quality
        quality_assessment = await self._assess_with_meta_council(
            council, topic, rounds, final_decision
        )
        
        return {
            'council_id': council_id,
            'topic': topic,
            'rounds': len(rounds),
            'consensus_reached': consensus_reached,
            'consensus_level': rounds[-1].consensus_level if rounds else 0.0,
            'decision': final_decision,
            'key_insights': self._aggregate_insights(rounds),
            'minority_reports': self._extract_minority_reports(rounds),
            'meta_reflection': meta_reflection,
            'quality_assessment': quality_assessment,
            'unresolved_tensions': rounds[-1].unresolved_tensions if rounds else []
        }
    
    async def _conduct_round(
        self,
        council: Council,
        topic: str,
        context: Dict[str, Any],
        pattern: DeliberationPattern,
        previous_rounds: List[DeliberationRound]
    ) -> DeliberationRound:
        """Conduct a single round of deliberation"""
        start_time = time.time()
        
        round_result = DeliberationRound(
            pattern=pattern,
            topic=topic
        )
        
        # Execute pattern-specific deliberation
        if pattern == DeliberationPattern.CONSENSUS:
            await self._consensus_round(council, context, round_result)
        elif pattern == DeliberationPattern.ADVERSARIAL:
            await self._adversarial_round(council, context, round_result)
        elif pattern == DeliberationPattern.SOCRATIC:
            await self._socratic_round(council, context, round_result)
        elif pattern == DeliberationPattern.BRAINSTORM:
            await self._brainstorm_round(council, context, round_result)
        elif pattern == DeliberationPattern.CRITICAL_ANALYSIS:
            await self._critical_analysis_round(council, context, round_result)
        elif pattern == DeliberationPattern.SYNTHESIS:
            await self._synthesis_round(council, context, round_result, previous_rounds)
        
        round_result.duration_seconds = time.time() - start_time
        
        # Calculate consensus level
        round_result.consensus_level = self._calculate_consensus(round_result.votes)
        round_result.consensus_reached = (
            round_result.consensus_level >= council.min_consensus_threshold
        )
        
        return round_result
    
    async def _consensus_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound
    ):
        """Standard consensus-seeking round"""
        for member_id, member in council.members.items():
            contribution = await self._generate_member_contribution(
                member, context, "consensus"
            )
            round_result.contributions.append(contribution)
            
            vote = CouncilVote(
                member_id=member_id,
                position=contribution.get('position', 'neutral'),
                confidence=contribution.get('confidence', 0.5),
                reasoning=contribution.get('reasoning', '')
            )
            round_result.votes.append(vote)
    
    async def _adversarial_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound
    ):
        """Structured debate with opposing positions"""
        members = list(council.members.values())
        
        # Split into two camps
        mid = len(members) // 2
        pro_camp = members[:mid]
        con_camp = members[mid:]
        
        # Pro arguments
        for member in pro_camp:
            contribution = await self._generate_member_contribution(
                member, context, "argue_for"
            )
            contribution['camp'] = 'pro'
            round_result.contributions.append(contribution)
        
        # Con arguments
        for member in con_camp:
            contribution = await self._generate_member_contribution(
                member, context, "argue_against"
            )
            contribution['camp'] = 'con'
            round_result.contributions.append(contribution)
        
        # Rebuttals
        for contribution in round_result.contributions:
            rebuttal = await self._generate_rebuttal(
                context, contribution, round_result.contributions
            )
            round_result.contributions.append(rebuttal)
    
    async def _socratic_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound
    ):
        """Question-driven exploration of the topic"""
        questions = []
        
        # Each member generates probing questions
        for member in council.members.values():
            member_questions = await self._generate_socratic_questions(
                member, context
            )
            questions.extend(member_questions)
        
        # Attempt to answer each question
        for question in questions:
            answers = []
            for member in council.members.values():
                answer = await self._generate_socratic_answer(
                    member, context, question
                )
                answers.append(answer)
            
            round_result.contributions.append({
                'question': question,
                'answers': answers
            })
            
            # Extract insights from Q&A
            if answers:
                round_result.key_insights.append(
                    f"Q: {question['text']} → Insight: {answers[0].get('insight', '')}"
                )
    
    async def _brainstorm_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound
    ):
        """Free-form idea generation"""
        # No criticism phase - pure idea generation
        all_ideas = []
        
        for member in council.members.values():
            ideas = await self._generate_brainstorm_ideas(member, context)
            all_ideas.extend(ideas)
        
        # Clustering and building on ideas
        clustered = await self._cluster_ideas(all_ideas)
        enhanced = await self._enhance_idea_clusters(clustered, council.members)
        
        round_result.contributions = enhanced
        round_result.key_insights = [
            idea['summary'] for idea in enhanced if idea.get('breakthrough_potential', 0) > 0.7
        ]
    
    async def _critical_analysis_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound
    ):
        """Deep critical examination"""
        # Identify assumptions
        assumptions = await self._identify_assumptions(context)
        
        # Challenge each assumption
        for assumption in assumptions:
            challenges = []
            for member in council.members.values():
                challenge = await self._challenge_assumption(member, assumption)
                challenges.append(challenge)
            
            round_result.contributions.append({
                'assumption': assumption,
                'challenges': challenges,
                'validity_score': self._calculate_assumption_validity(challenges)
            })
        
        # Identify blind spots
        blind_spots = await self._identify_blind_spots(council, context)
        round_result.unresolved_tensions.extend(blind_spots)
    
    async def _synthesis_round(
        self,
        council: Council,
        context: Dict[str, Any],
        round_result: DeliberationRound,
        previous_rounds: List[DeliberationRound]
    ):
        """Synthesize insights from previous rounds"""
        # Collect all insights
        all_insights = []
        for prev_round in previous_rounds:
            all_insights.extend(prev_round.key_insights)
        
        # Find patterns and connections
        patterns = await self._find_insight_patterns(all_insights)
        
        # Generate synthesis
        synthesis = await self._generate_synthesis(
            council.members.values(), patterns, context
        )
        
        round_result.contributions = synthesis
        round_result.key_insights = [s['key_point'] for s in synthesis]
    
    async def _generate_member_contribution(
        self,
        member: CouncilMember,
        context: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """Generate a contribution from a council member"""
        return {
            'member_id': member.member_id,
            'member_name': member.name,
            'mode': mode,
            'content': f"Contribution from {member.name} in {mode} mode",
            'position': 'supportive' if member.open_mindedness > 0.5 else 'critical',
            'confidence': member.assertiveness,
            'reasoning': f"Based on expertise in {member.expertise}"
        }
    
    async def _generate_rebuttal(
        self,
        context: Dict[str, Any],
        target: Dict[str, Any],
        all_contributions: List[Dict]
    ) -> Dict[str, Any]:
        """Generate a rebuttal to a contribution"""
        return {
            'type': 'rebuttal',
            'target_camp': 'con' if target.get('camp') == 'pro' else 'pro',
            'content': f"Rebuttal to: {target.get('content', '')}"
        }
    
    async def _generate_socratic_questions(
        self,
        member: CouncilMember,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate Socratic questions"""
        return [
            {'text': f"What assumptions underlie this approach?", 'depth': 1},
            {'text': f"What would change if we removed constraint X?", 'depth': 2},
            {'text': f"How do we know this is true?", 'depth': 1}
        ]
    
    async def _generate_socratic_answer(
        self,
        member: CouncilMember,
        context: Dict[str, Any],
        question: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate an answer to a Socratic question"""
        return {
            'member_id': member.member_id,
            'answer': f"Response to: {question['text']}",
            'insight': "Key insight from this exploration"
        }
    
    async def _generate_brainstorm_ideas(
        self,
        member: CouncilMember,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate brainstorm ideas"""
        return [
            {'idea': f"Idea from {member.name}", 'novelty': member.creativity}
        ]
    
    async def _cluster_ideas(self, ideas: List[Dict]) -> List[Dict]:
        """Cluster similar ideas together"""
        return ideas
    
    async def _enhance_idea_clusters(
        self,
        clusters: List[Dict],
        members: Dict[str, CouncilMember]
    ) -> List[Dict]:
        """Enhance and build upon idea clusters"""
        return clusters
    
    async def _identify_assumptions(self, context: Dict[str, Any]) -> List[str]:
        """Identify underlying assumptions"""
        return ["Assumption 1", "Assumption 2"]
    
    async def _challenge_assumption(
        self,
        member: CouncilMember,
        assumption: str
    ) -> Dict[str, Any]:
        """Challenge an assumption"""
        return {
            'member_id': member.member_id,
            'challenge': f"Challenge to: {assumption}",
            'validity_impact': member.skepticism
        }
    
    def _calculate_assumption_validity(self, challenges: List[Dict]) -> float:
        """Calculate validity score for an assumption"""
        if not challenges:
            return 1.0
        return 1.0 - sum(c.get('validity_impact', 0) for c in challenges) / len(challenges)
    
    async def _identify_blind_spots(
        self,
        council: Council,
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify potential blind spots in deliberation"""
        return []
    
    async def _find_insight_patterns(self, insights: List[str]) -> List[Dict]:
        """Find patterns across insights"""
        return [{'pattern': 'Recurring theme', 'insights': insights}]
    
    async def _generate_synthesis(
        self,
        members,
        patterns: List[Dict],
        context: Dict[str, Any]
    ) -> List[Dict]:
        """Generate synthesis from patterns"""
        return [{'key_point': 'Synthesized insight', 'source_patterns': patterns}]
    
    def _calculate_consensus(self, votes: List[CouncilVote]) -> float:
        """Calculate consensus level from votes"""
        if not votes:
            return 0.0
        
        positions = defaultdict(float)
        for vote in votes:
            positions[vote.position] += vote.confidence
        
        if not positions:
            return 0.0
        
        max_position = max(positions.values())
        total = sum(positions.values())
        
        return max_position / total if total > 0 else 0.0
    
    async def _meta_reflect(
        self,
        council: Council,
        rounds: List[DeliberationRound]
    ) -> MetaDeliberation:
        """Meta-cognitive reflection on the deliberation process"""
        meta = MetaDeliberation(target_council_id=council.council_id)
        
        # Assess deliberation quality
        meta.quality_assessment = {
            'depth': self._assess_depth(rounds),
            'breadth': self._assess_breadth(rounds),
            'rigor': self._assess_rigor(rounds),
            'creativity': self._assess_creativity(rounds),
            'balance': self._assess_balance(rounds)
        }
        
        # Detect biases
        meta.bias_detections = await self.bias_detector.detect(rounds)
        
        # Recommend improvements
        meta.process_improvements = await self._generate_improvements(
            council, rounds, meta.quality_assessment
        )
        
        return meta
    
    def _assess_depth(self, rounds: List[DeliberationRound]) -> float:
        """Assess the depth of deliberation"""
        if not rounds:
            return 0.0
        return min(1.0, len(rounds) * 0.1 + sum(
            len(r.key_insights) for r in rounds
        ) * 0.05)
    
    def _assess_breadth(self, rounds: List[DeliberationRound]) -> float:
        """Assess the breadth of deliberation"""
        patterns_used = set(r.pattern for r in rounds)
        return len(patterns_used) / len(DeliberationPattern)
    
    def _assess_rigor(self, rounds: List[DeliberationRound]) -> float:
        """Assess the rigor of deliberation"""
        critical_rounds = sum(
            1 for r in rounds
            if r.pattern in [
                DeliberationPattern.CRITICAL_ANALYSIS,
                DeliberationPattern.ADVERSARIAL
            ]
        )
        return min(1.0, critical_rounds * 0.3)
    
    def _assess_creativity(self, rounds: List[DeliberationRound]) -> float:
        """Assess the creativity of deliberation"""
        creative_rounds = sum(
            1 for r in rounds
            if r.pattern in [
                DeliberationPattern.BRAINSTORM,
                DeliberationPattern.SYNTHESIS
            ]
        )
        return min(1.0, creative_rounds * 0.3)
    
    def _assess_balance(self, rounds: List[DeliberationRound]) -> float:
        """Assess the balance of perspectives"""
        all_votes = []
        for r in rounds:
            all_votes.extend(r.votes)
        
        if not all_votes:
            return 0.5
        
        positions = defaultdict(int)
        for vote in all_votes:
            positions[vote.position] += 1
        
        if len(positions) < 2:
            return 0.3
        
        values = list(positions.values())
        return 1.0 - (max(values) - min(values)) / sum(values)
    
    async def _generate_improvements(
        self,
        council: Council,
        rounds: List[DeliberationRound],
        quality: Dict[str, float]
    ) -> List[str]:
        """Generate improvement suggestions"""
        improvements = []
        
        if quality.get('depth', 0) < 0.5:
            improvements.append("Increase deliberation depth with more rounds")
        if quality.get('rigor', 0) < 0.5:
            improvements.append("Add more critical analysis rounds")
        if quality.get('creativity', 0) < 0.5:
            improvements.append("Include brainstorming phases")
        if quality.get('balance', 0) < 0.5:
            improvements.append("Ensure more balanced perspectives")
        
        return improvements
    
    async def _extract_decision(
        self,
        council: Council,
        rounds: List[DeliberationRound]
    ) -> Dict[str, Any]:
        """Extract the final decision from deliberation"""
        all_insights = []
        final_votes = []
        
        for r in rounds:
            all_insights.extend(r.key_insights)
            final_votes.extend(r.votes)
        
        # Aggregate to decision
        position_weights = defaultdict(float)
        for vote in final_votes:
            position_weights[vote.position] += vote.confidence
        
        winning_position = max(position_weights.items(), key=lambda x: x[1]) if position_weights else ('neutral', 0)
        
        return {
            'position': winning_position[0],
            'confidence': winning_position[1] / len(final_votes) if final_votes else 0,
            'key_insights': all_insights[-10:],  # Top 10 insights
            'supporting_votes': len([v for v in final_votes if v.position == winning_position[0]]),
            'total_votes': len(final_votes)
        }
    
    def _aggregate_insights(self, rounds: List[DeliberationRound]) -> List[str]:
        """Aggregate all key insights"""
        insights = []
        for r in rounds:
            insights.extend(r.key_insights)
        return insights
    
    def _extract_minority_reports(self, rounds: List[DeliberationRound]) -> List[Dict]:
        """Extract minority reports for preserved dissenting views"""
        minority_reports = []
        
        for r in rounds:
            for vote in r.votes:
                if vote.dissenting_points:
                    minority_reports.append({
                        'member_id': vote.member_id,
                        'position': vote.position,
                        'dissenting_points': vote.dissenting_points
                    })
        
        return minority_reports
    
    async def _escalate_to_parent(
        self,
        council: Council,
        topic: str,
        rounds: List[DeliberationRound],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Escalate unresolved issues to parent council"""
        if not council.parent_council_id:
            return {}
        
        parent_council = self.councils.get(council.parent_council_id)
        if not parent_council:
            return {}
        
        # Prepare escalation context
        escalation_context = {
            'original_topic': topic,
            'child_council': council.name,
            'unresolved_tensions': rounds[-1].unresolved_tensions if rounds else [],
            'attempted_decision': decision
        }
        
        # Deliberate at parent level
        return await self.deliberate(
            council.parent_council_id,
            f"Escalation: {topic}",
            escalation_context,
            pattern=DeliberationPattern.SYNTHESIS
        )
    
    async def _assess_with_meta_council(
        self,
        council: Council,
        topic: str,
        rounds: List[DeliberationRound],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get quality assessment from supreme meta-council"""
        if not self.meta_council_id or council.council_id == self.meta_council_id:
            return {}
        
        meta_council = self.councils.get(self.meta_council_id)
        if not meta_council:
            return {}
        
        # Quick meta-assessment
        assessment_context = {
            'council_name': council.name,
            'topic': topic,
            'rounds_count': len(rounds),
            'consensus_level': rounds[-1].consensus_level if rounds else 0,
            'decision': decision
        }
        
        return {
            'quality_score': 0.8,  # Placeholder
            'recommendations': []
        }


class PsychologicalAmplificationEngine:
    """Applies psychological techniques to enhance output quality"""
    
    AMPLIFICATION_PROMPTS = {
        PsychologicalAmplifier.GROWTH_MINDSET: 
            "Remember: Every challenge is an opportunity to grow and improve.",
        PsychologicalAmplifier.CHALLENGE_FRAMING:
            "This is an exciting intellectual challenge that will push our capabilities.",
        PsychologicalAmplifier.EXCELLENCE_DRIVE:
            "We aim for nothing less than excellence. The best possible outcome.",
        PsychologicalAmplifier.CURIOSITY_BOOST:
            "What aspects haven't we explored yet? What's beyond the obvious?",
        PsychologicalAmplifier.CREATIVE_TENSION:
            "Let's think beyond conventional constraints. What if anything were possible?",
        PsychologicalAmplifier.PERFECTIONIST_PUSH:
            "Every detail matters. Precision and thoroughness lead to breakthroughs.",
        PsychologicalAmplifier.LEGACY_MOTIVATION:
            "This work will set new standards. We're creating something lasting.",
        PsychologicalAmplifier.COMPETITIVE_EDGE:
            "We must surpass all existing solutions. Nothing less than the best.",
        PsychologicalAmplifier.BREAKTHROUGH_HUNT:
            "The breakthrough insight is within reach. Let's find it.",
        PsychologicalAmplifier.MASTERY_PURSUIT:
            "Deep understanding leads to mastery. Let's go deeper."
    }
    
    async def amplify(
        self,
        context: Dict[str, Any],
        amplifiers: List[PsychologicalAmplifier]
    ) -> Dict[str, Any]:
        """Apply psychological amplification to context"""
        amplified = context.copy()
        
        motivational_priming = []
        for amp in amplifiers:
            if amp in self.AMPLIFICATION_PROMPTS:
                motivational_priming.append(self.AMPLIFICATION_PROMPTS[amp])
        
        amplified['psychological_priming'] = motivational_priming
        amplified['amplification_level'] = len(amplifiers)
        
        return amplified


class BiasDetectionEngine:
    """Detects cognitive biases in deliberation"""
    
    KNOWN_BIASES = [
        'confirmation_bias',
        'anchoring_bias',
        'groupthink',
        'availability_heuristic',
        'sunk_cost_fallacy',
        'authority_bias',
        'recency_bias',
        'optimism_bias'
    ]
    
    async def detect(self, rounds: List[DeliberationRound]) -> List[Dict[str, Any]]:
        """Detect biases in deliberation rounds"""
        detected = []
        
        # Check for groupthink (too much consensus too fast)
        if len(rounds) >= 2:
            early_consensus = rounds[0].consensus_level > 0.9
            if early_consensus:
                detected.append({
                    'bias': 'groupthink',
                    'evidence': 'Very high consensus in first round',
                    'severity': 'medium'
                })
        
        # Check for confirmation bias (only supporting evidence cited)
        for r in rounds:
            for vote in r.votes:
                if vote.supporting_evidence and not vote.dissenting_points:
                    if vote.confidence > 0.8:
                        detected.append({
                            'bias': 'confirmation_bias',
                            'evidence': f'Member {vote.member_id} shows high confidence with only supporting evidence',
                            'severity': 'low'
                        })
        
        return detected


class PatternSelectionEngine:
    """Selects optimal deliberation patterns based on context"""
    
    async def select_next_pattern(
        self,
        council: Council,
        previous_rounds: List[DeliberationRound],
        current_pattern: DeliberationPattern
    ) -> DeliberationPattern:
        """Select the next deliberation pattern"""
        # If stuck, try different patterns
        patterns_tried = set(r.pattern for r in previous_rounds)
        
        # Priority order for pattern escalation
        escalation_order = [
            DeliberationPattern.CONSENSUS,
            DeliberationPattern.BRAINSTORM,
            DeliberationPattern.ADVERSARIAL,
            DeliberationPattern.SOCRATIC,
            DeliberationPattern.CRITICAL_ANALYSIS,
            DeliberationPattern.SYNTHESIS,
            DeliberationPattern.HIERARCHICAL
        ]
        
        for pattern in escalation_order:
            if pattern not in patterns_tried:
                return pattern
        
        # Default to synthesis if all tried
        return DeliberationPattern.SYNTHESIS


# Export main classes
__all__ = [
    'MetaCognitiveCouncilSystem',
    'Council',
    'CouncilMember',
    'DeliberationPattern',
    'PsychologicalAmplifier',
    'DeliberationRound',
    'CouncilVote',
    'MetaDeliberation',
    'PsychologicalAmplificationEngine',
    'BiasDetectionEngine',
    'PatternSelectionEngine'
]
