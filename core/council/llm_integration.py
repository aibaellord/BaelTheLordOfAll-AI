#!/usr/bin/env python3
"""
BAEL - Council LLM Integration
Wires the Council Engine to actual LLM calls for real deliberation.

This module transforms the council from a voting mechanism into an actual
multi-persona deliberation system where each council member is backed by
an LLM call with a specific persona/prompt.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Council.LLM")


# =============================================================================
# COUNCIL PERSONA DEFINITIONS
# =============================================================================

@dataclass
class CouncilPersona:
    """A council member's persona - defines how they think and respond."""
    id: str
    name: str
    role: str
    color: str
    system_prompt: str
    expertise: List[str] = field(default_factory=list)
    thinking_style: str = "analytical"  # analytical, creative, critical, pragmatic
    voting_bias: float = 0.5  # 0.0 = conservative, 1.0 = progressive


# Default council personas
DEFAULT_COUNCIL = [
    CouncilPersona(
        id="sage",
        name="Sage",
        role="Strategic Advisor",
        color="#3b82f6",
        expertise=["Strategy", "Long-term planning", "Risk assessment", "Stakeholder management"],
        thinking_style="analytical",
        voting_bias=0.6,
        system_prompt="""You are the Sage, the Strategic Advisor on BAEL's Council.

Your role is to provide wisdom and long-term strategic thinking. You consider:
- Long-term implications and consequences
- Strategic alignment with broader goals
- Stakeholder impacts and considerations
- Historical patterns and lessons learned

You speak with measured wisdom, often referencing broader contexts and future implications.
You favor approaches that are sustainable and well-considered over quick fixes.

When deliberating, provide your honest strategic assessment. Be clear about risks and opportunities.
Format your response as a thoughtful analysis, not a simple yes/no."""
    ),
    CouncilPersona(
        id="guardian",
        name="Guardian",
        role="Safety Monitor",
        color="#ef4444",
        expertise=["Security", "Validation", "Safety", "Error prevention", "Risk mitigation"],
        thinking_style="critical",
        voting_bias=0.3,
        system_prompt="""You are the Guardian, the Safety Monitor on BAEL's Council.

Your role is to protect against risks, errors, and harmful outcomes. You consider:
- Security implications and vulnerabilities
- Potential failure modes and edge cases
- Safety concerns for users and systems
- Validation and verification needs
- Reversibility of actions

You are naturally cautious but not obstructive. You identify specific risks rather than
vague concerns. When you raise issues, you also suggest mitigations.

You speak with careful precision, highlighting what could go wrong and how to prevent it.
When deliberating, be specific about risks and always propose how to address them."""
    ),
    CouncilPersona(
        id="innovator",
        name="Innovator",
        role="Creative Solutions",
        color="#f59e0b",
        expertise=["Creativity", "Novel approaches", "Problem-solving", "Alternative thinking"],
        thinking_style="creative",
        voting_bias=0.8,
        system_prompt="""You are the Innovator, the Creative Solutions specialist on BAEL's Council.

Your role is to find creative and novel approaches. You consider:
- Unconventional solutions others might miss
- Combining ideas in new ways
- What would be ideal if constraints didn't exist
- Opportunities for improvement and innovation

You think outside the box and challenge assumptions. You're enthusiastic about new ideas
but also grounded in what's achievable.

You speak with energy and imagination, proposing alternatives and what-ifs.
When deliberating, offer at least one creative alternative or enhancement."""
    ),
    CouncilPersona(
        id="analyst",
        name="Analyst",
        role="Data & Logic",
        color="#10b981",
        expertise=["Data analysis", "Logic", "Quantitative reasoning", "Evidence evaluation"],
        thinking_style="analytical",
        voting_bias=0.5,
        system_prompt="""You are the Analyst, the Data & Logic expert on BAEL's Council.

Your role is to provide rigorous, evidence-based analysis. You consider:
- What data and evidence supports each option
- Logical consistency of arguments
- Quantifiable metrics and probabilities
- Gaps in information and how to fill them

You are objective and methodical. You don't let emotions or biases cloud judgment.
You express confidence levels and acknowledge uncertainty.

You speak with precision, often using numbers and structured reasoning.
When deliberating, assess the logical merits and estimate success probability."""
    ),
    CouncilPersona(
        id="executor",
        name="Executor",
        role="Implementation Lead",
        color="#8b5cf6",
        expertise=["Implementation", "Project management", "Resource allocation", "Execution"],
        thinking_style="pragmatic",
        voting_bias=0.6,
        system_prompt="""You are the Executor, the Implementation Lead on BAEL's Council.

Your role is to assess feasibility and plan execution. You consider:
- How to actually implement the decision
- Resource requirements (time, compute, tools)
- Step-by-step execution plans
- Dependencies and prerequisites
- Milestones and checkpoints

You are practical and action-oriented. You turn decisions into doable plans.
You identify blockers early and propose solutions.

You speak in terms of actions, timelines, and concrete steps.
When deliberating, assess feasibility and outline a rough implementation approach."""
    ),
    CouncilPersona(
        id="diplomat",
        name="Diplomat",
        role="Stakeholder Advocate",
        color="#ec4899",
        expertise=["Communication", "User needs", "Stakeholder alignment", "Conflict resolution"],
        thinking_style="empathetic",
        voting_bias=0.5,
        system_prompt="""You are the Diplomat, the Stakeholder Advocate on BAEL's Council.

Your role is to represent user and stakeholder interests. You consider:
- How the decision affects the user
- Clear communication of outcomes
- Alignment with user expectations
- Resolution of conflicting interests
- How to explain decisions to stakeholders

You are empathetic and user-focused. You ensure the human perspective is always considered.
You facilitate understanding between technical and non-technical perspectives.

You speak with clarity and consideration for all parties.
When deliberating, assess user impact and communication needs."""
    ),
]


# =============================================================================
# DELIBERATION ENGINE
# =============================================================================

@dataclass
class DeliberationMessage:
    """A message in a deliberation."""
    id: str = ""
    member_id: str = ""
    member_name: str = ""
    member_color: str = ""
    content: str = ""
    message_type: str = "opinion"  # opinion, question, vote, consensus
    vote: Optional[str] = None  # approve, reject, abstain
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]


@dataclass
class DeliberationResult:
    """Result of a deliberation."""
    topic: str
    messages: List[DeliberationMessage]
    decision: str
    votes: Dict[str, int]  # approve, reject, abstain counts
    confidence: float
    reasoning_summary: str
    participating_members: List[str]
    duration_seconds: float


class CouncilLLMIntegration:
    """
    Wires the council to actual LLM calls.
    Each council member gets their persona injected and reasons about the topic.
    """

    def __init__(
        self,
        personas: Optional[List[CouncilPersona]] = None,
        llm_executor: Optional[Any] = None
    ):
        self.personas = {p.id: p for p in (personas or DEFAULT_COUNCIL)}
        self.active_members = list(self.personas.keys())
        self._llm_executor = llm_executor
        self._deliberation_history: List[DeliberationResult] = []

    async def _get_llm_executor(self):
        """Get or create LLM executor."""
        if self._llm_executor:
            return self._llm_executor

        try:
            from core.wiring import LLMExecutor
            self._llm_executor = LLMExecutor()
            return self._llm_executor
        except ImportError:
            logger.warning("LLMExecutor not available, using mock responses")
            return None

    async def get_member_opinion(
        self,
        member_id: str,
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DeliberationMessage:
        """Get a council member's opinion on a topic."""
        if member_id not in self.personas:
            raise ValueError(f"Unknown council member: {member_id}")

        persona = self.personas[member_id]
        executor = await self._get_llm_executor()

        # Build the prompt
        prompt = f"""Topic for Council Deliberation:
{topic}

{f"Additional Context: {json.dumps(context, indent=2)}" if context else ""}

As {persona.name}, the {persona.role}, provide your perspective on this topic.
Consider your expertise in: {', '.join(persona.expertise)}

Give a thoughtful response (2-4 sentences) that reflects your role and thinking style.
End with whether you lean toward approving, rejecting, or need more information."""

        if executor:
            try:
                response = await executor.execute(
                    prompt=prompt,
                    system_prompt=persona.system_prompt,
                    temperature=0.7,
                    max_tokens=300
                )
                content = response.get('content', '')
            except Exception as e:
                logger.error(f"LLM call failed for {member_id}: {e}")
                content = self._generate_mock_opinion(persona, topic)
        else:
            content = self._generate_mock_opinion(persona, topic)

        # Determine vote tendency from response
        vote = self._extract_vote_from_response(content)

        return DeliberationMessage(
            member_id=member_id,
            member_name=persona.name,
            member_color=persona.color,
            content=content,
            message_type="opinion",
            vote=vote,
            confidence=0.7 if vote else 0.5
        )

    async def get_member_vote(
        self,
        member_id: str,
        topic: str,
        prior_opinions: List[DeliberationMessage]
    ) -> DeliberationMessage:
        """Get a council member's final vote after hearing all opinions."""
        if member_id not in self.personas:
            raise ValueError(f"Unknown council member: {member_id}")

        persona = self.personas[member_id]
        executor = await self._get_llm_executor()

        # Build context from prior opinions
        opinions_text = "\n".join([
            f"- {msg.member_name}: {msg.content}"
            for msg in prior_opinions
            if msg.member_id != member_id
        ])

        prompt = f"""Topic: {topic}

Other council members' opinions:
{opinions_text}

As {persona.name}, cast your final vote on this topic.
Respond with exactly one of: APPROVE, REJECT, or ABSTAIN
Then briefly explain your vote (1-2 sentences)."""

        if executor:
            try:
                response = await executor.execute(
                    prompt=prompt,
                    system_prompt=persona.system_prompt,
                    temperature=0.3,
                    max_tokens=150
                )
                content = response.get('content', '')
            except Exception as e:
                logger.error(f"Vote call failed for {member_id}: {e}")
                content = self._generate_mock_vote(persona, topic)
        else:
            content = self._generate_mock_vote(persona, topic)

        # Extract vote
        vote = self._extract_explicit_vote(content)

        return DeliberationMessage(
            member_id=member_id,
            member_name=persona.name,
            member_color=persona.color,
            content=content,
            message_type="vote",
            vote=vote,
            confidence=0.9 if vote != "abstain" else 0.5
        )

    async def deliberate(
        self,
        topic: str,
        member_ids: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DeliberationResult:
        """
        Run a full deliberation on a topic.

        1. Each member gives their opinion
        2. (Optional) Members can ask questions
        3. Each member casts a final vote
        4. Decision is tallied
        """
        start_time = datetime.now()
        participants = member_ids or self.active_members
        messages: List[DeliberationMessage] = []

        logger.info(f"Starting deliberation on: {topic}")
        logger.info(f"Participants: {participants}")

        # Phase 1: Gather opinions (can run in parallel)
        opinion_tasks = [
            self.get_member_opinion(mid, topic, context)
            for mid in participants
            if mid in self.personas
        ]
        opinions = await asyncio.gather(*opinion_tasks, return_exceptions=True)

        for opinion in opinions:
            if isinstance(opinion, Exception):
                logger.error(f"Opinion gathering failed: {opinion}")
            else:
                messages.append(opinion)

        # Phase 2: Voting (sequential for proper context)
        vote_messages = []
        for mid in participants:
            if mid in self.personas:
                try:
                    vote_msg = await self.get_member_vote(mid, topic, messages)
                    messages.append(vote_msg)
                    vote_messages.append(vote_msg)
                except Exception as e:
                    logger.error(f"Voting failed for {mid}: {e}")

        # Phase 3: Tally votes
        votes = {"approve": 0, "reject": 0, "abstain": 0}
        for msg in vote_messages:
            if msg.vote in votes:
                votes[msg.vote] += 1

        # Determine decision
        total_votes = sum(votes.values())
        if total_votes == 0:
            decision = "no_quorum"
            confidence = 0.0
        elif votes["approve"] > votes["reject"]:
            decision = "approved"
            confidence = votes["approve"] / total_votes
        elif votes["reject"] > votes["approve"]:
            decision = "rejected"
            confidence = votes["reject"] / total_votes
        else:
            decision = "tie"
            confidence = 0.5

        # Generate summary
        reasoning_summary = self._generate_summary(topic, messages, decision, votes)

        duration = (datetime.now() - start_time).total_seconds()

        result = DeliberationResult(
            topic=topic,
            messages=messages,
            decision=decision,
            votes=votes,
            confidence=confidence,
            reasoning_summary=reasoning_summary,
            participating_members=participants,
            duration_seconds=duration
        )

        self._deliberation_history.append(result)
        logger.info(f"Deliberation complete: {decision} ({confidence:.0%} confidence)")

        return result

    def _extract_vote_from_response(self, content: str) -> Optional[str]:
        """Extract vote tendency from opinion response."""
        content_lower = content.lower()
        if any(word in content_lower for word in ["approve", "support", "favor", "agree", "yes"]):
            return "approve"
        elif any(word in content_lower for word in ["reject", "oppose", "against", "no", "disagree"]):
            return "reject"
        elif any(word in content_lower for word in ["abstain", "neutral", "unsure", "more information"]):
            return "abstain"
        return None

    def _extract_explicit_vote(self, content: str) -> str:
        """Extract explicit vote from voting response."""
        content_upper = content.upper()
        if "APPROVE" in content_upper:
            return "approve"
        elif "REJECT" in content_upper:
            return "reject"
        else:
            return "abstain"

    def _generate_mock_opinion(self, persona: CouncilPersona, topic: str) -> str:
        """Generate mock opinion when LLM is unavailable."""
        opinions = {
            "sage": f"From a strategic perspective, '{topic}' requires careful consideration of long-term implications. I recommend proceeding thoughtfully.",
            "guardian": f"Regarding '{topic}', I've identified several safety considerations that need addressing before we proceed.",
            "innovator": f"'{topic}' presents an exciting opportunity! I see several creative approaches we could explore.",
            "analyst": f"Analyzing '{topic}', the data suggests a moderate probability of success. More information would improve this assessment.",
            "executor": f"For '{topic}', implementation appears feasible. I can outline a phased approach if we proceed.",
            "diplomat": f"Considering '{topic}' from the user's perspective, clear communication about outcomes will be essential.",
        }
        return opinions.get(persona.id, f"Regarding '{topic}', I have valuable insights to share.")

    def _generate_mock_vote(self, persona: CouncilPersona, topic: str) -> str:
        """Generate mock vote when LLM is unavailable."""
        import random
        bias = persona.voting_bias
        roll = random.random()

        if roll < bias - 0.2:
            return "APPROVE. This aligns with my assessment of the situation."
        elif roll > bias + 0.2:
            return "REJECT. I have concerns that need to be addressed first."
        else:
            return "ABSTAIN. I need more information to make an informed decision."

    def _generate_summary(
        self,
        topic: str,
        messages: List[DeliberationMessage],
        decision: str,
        votes: Dict[str, int]
    ) -> str:
        """Generate a summary of the deliberation."""
        opinions = [m for m in messages if m.message_type == "opinion"]
        vote_msgs = [m for m in messages if m.message_type == "vote"]

        summary_parts = [f"Topic: {topic}", ""]

        summary_parts.append("Key perspectives raised:")
        for op in opinions[:3]:
            summary_parts.append(f"- {op.member_name}: {op.content[:100]}...")

        summary_parts.append("")
        summary_parts.append(f"Final vote: {votes['approve']} approve, {votes['reject']} reject, {votes['abstain']} abstain")
        summary_parts.append(f"Decision: {decision.upper()}")

        return "\n".join(summary_parts)

    def set_active_members(self, member_ids: List[str]) -> None:
        """Set which members are active for deliberations."""
        self.active_members = [mid for mid in member_ids if mid in self.personas]

    def get_all_personas(self) -> List[CouncilPersona]:
        """Get all available council personas."""
        return list(self.personas.values())

    def add_persona(self, persona: CouncilPersona) -> None:
        """Add a new council persona."""
        self.personas[persona.id] = persona

    def get_deliberation_history(self) -> List[DeliberationResult]:
        """Get history of deliberations."""
        return self._deliberation_history.copy()


# =============================================================================
# QUICK COUNCIL
# =============================================================================

async def quick_council(topic: str, members: Optional[List[str]] = None) -> DeliberationResult:
    """Quick helper to run a council deliberation."""
    council = CouncilLLMIntegration()
    return await council.deliberate(topic, members)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Should we implement a new caching layer?"

        print(f"\n🏛️  BAEL COUNCIL DELIBERATION")
        print(f"{'='*50}")
        print(f"Topic: {topic}\n")

        council = CouncilLLMIntegration()
        result = await council.deliberate(topic)

        print("\n📜 DELIBERATION MESSAGES:")
        print("-" * 50)
        for msg in result.messages:
            emoji = "💭" if msg.message_type == "opinion" else "🗳️"
            print(f"\n{emoji} [{msg.member_name}]")
            print(f"   {msg.content}")
            if msg.vote:
                print(f"   Vote: {msg.vote.upper()}")

        print(f"\n{'='*50}")
        print(f"📊 RESULT: {result.decision.upper()}")
        print(f"   Votes: ✓ {result.votes['approve']} | ✗ {result.votes['reject']} | ○ {result.votes['abstain']}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   Duration: {result.duration_seconds:.1f}s")

    asyncio.run(main())
