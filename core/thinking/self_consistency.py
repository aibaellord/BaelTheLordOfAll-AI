"""
BAEL - Self-Consistency Reasoning
Multi-sample voting for robust conclusions.
Generates multiple independent reasoning chains and votes on the answer.
"""

import asyncio
import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import ThinkingConfig, ThinkingMode, ThinkingStep, ThinkingTrace

logger = logging.getLogger("BAEL.Thinking.SelfConsistency")


@dataclass
class ReasoningPath:
    """A single reasoning path."""
    id: str
    chain: List[str]
    final_answer: str
    confidence: float
    reasoning_style: str  # analytical, intuitive, systematic, creative
    token_count: int = 0


@dataclass
class ConsensusResult:
    """Result of consensus voting."""
    winning_answer: str
    vote_count: int
    total_votes: int
    agreement_ratio: float
    alternative_answers: List[Tuple[str, int]]
    paths_used: List[str]


@dataclass
class ConsistencyConfig:
    """Configuration for self-consistency."""
    num_samples: int = 5
    temperature_range: Tuple[float, float] = (0.5, 0.9)
    diverse_prompts: bool = True
    vote_threshold: float = 0.4  # Minimum agreement to accept
    normalize_answers: bool = True
    parallel_generation: bool = True


class SelfConsistency:
    """
    Self-Consistency reasoning engine.

    Generates multiple independent reasoning chains with varied:
    - Temperatures (randomness)
    - Prompting styles
    - Reasoning approaches

    Then aggregates via majority voting for robust answers.
    """

    def __init__(self, config: Optional[ConsistencyConfig] = None):
        self.config = config or ConsistencyConfig()
        self._llm = None

        # Different reasoning styles for diversity
        self._reasoning_styles = [
            ("analytical", "Step by step, analyze each component logically."),
            ("intuitive", "Trust your intuition and make reasonable assumptions."),
            ("systematic", "Follow a structured methodology, checking each step."),
            ("creative", "Think outside the box, consider unconventional approaches."),
            ("skeptical", "Question assumptions and consider edge cases."),
        ]

    async def _get_llm(self):
        """Lazy load LLM provider."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                from .extended_thinking import MockLLM
                self._llm = MockLLM()
        return self._llm

    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ThinkingTrace:
        """
        Perform self-consistent reasoning with voting.

        Args:
            query: The problem to solve
            context: Additional context

        Returns:
            ThinkingTrace with consensus answer
        """
        logger.info(f"Starting self-consistency reasoning with {self.config.num_samples} samples")

        # Generate multiple reasoning paths
        if self.config.parallel_generation:
            paths = await asyncio.gather(*[
                self._generate_path(query, i)
                for i in range(self.config.num_samples)
            ])
        else:
            paths = []
            for i in range(self.config.num_samples):
                path = await self._generate_path(query, i)
                paths.append(path)

        # Vote on answers
        consensus = self._vote(paths)

        # Build trace
        trace = self._build_trace(query, paths, consensus)

        logger.info(f"Consensus reached: {consensus.agreement_ratio:.2%} agreement")

        return trace

    async def _generate_path(
        self,
        query: str,
        sample_index: int
    ) -> ReasoningPath:
        """Generate a single reasoning path."""
        llm = await self._get_llm()

        # Vary temperature across samples
        temp_min, temp_max = self.config.temperature_range
        temp_step = (temp_max - temp_min) / max(self.config.num_samples - 1, 1)
        temperature = temp_min + (sample_index * temp_step)

        # Select reasoning style
        style_name, style_prompt = self._reasoning_styles[
            sample_index % len(self._reasoning_styles)
        ]

        # Build prompt
        if self.config.diverse_prompts:
            prompt = self._get_diverse_prompt(query, style_name, style_prompt)
        else:
            prompt = self._get_standard_prompt(query)

        # Generate
        response = await llm.generate(prompt, temperature=temperature)

        # Parse response
        chain, answer = self._parse_response(response)

        # Estimate confidence from response
        confidence = self._estimate_confidence(response)

        return ReasoningPath(
            id=f"path_{uuid.uuid4().hex[:8]}",
            chain=chain,
            final_answer=answer,
            confidence=confidence,
            reasoning_style=style_name,
            token_count=len(response.split())
        )

    def _get_standard_prompt(self, query: str) -> str:
        """Get standard reasoning prompt."""
        return f"""Solve this problem step by step.

PROBLEM: {query}

Think through this carefully:
1. [First step]
2. [Next step]
...

FINAL ANSWER: [Your answer]"""

    def _get_diverse_prompt(
        self,
        query: str,
        style_name: str,
        style_instruction: str
    ) -> str:
        """Get diverse reasoning prompt based on style."""
        prompts = {
            "analytical": f"""Analyze this problem methodically.

PROBLEM: {query}

ANALYSIS:
- Break down the components
- Examine relationships
- Draw logical conclusions

REASONING:
[Your step-by-step analysis]

FINAL ANSWER: [Your answer]""",

            "intuitive": f"""Consider this problem and trust your reasoning.

PROBLEM: {query}

INTUITION:
What seems most likely or reasonable?

REASONING:
[Your thought process]

FINAL ANSWER: [Your answer]""",

            "systematic": f"""Apply a systematic approach to this problem.

PROBLEM: {query}

METHODOLOGY:
1. Identify given information
2. Determine what's being asked
3. Apply relevant principles
4. Verify the solution

SYSTEMATIC REASONING:
[Your structured approach]

FINAL ANSWER: [Your answer]""",

            "creative": f"""Think creatively about this problem.

PROBLEM: {query}

CREATIVE EXPLORATION:
- What if we approach this differently?
- Are there unusual connections?
- What would be an elegant solution?

REASONING:
[Your creative thinking]

FINAL ANSWER: [Your answer]""",

            "skeptical": f"""Critically evaluate this problem.

PROBLEM: {query}

CRITICAL ANALYSIS:
- What assumptions are we making?
- What could go wrong?
- Are there edge cases?

REASONING:
[Your critical analysis]

FINAL ANSWER: [Your answer]"""
        }

        return prompts.get(style_name, self._get_standard_prompt(query))

    def _parse_response(self, response: str) -> Tuple[List[str], str]:
        """Parse reasoning chain and final answer from response."""
        chain = []
        answer = ""

        # Extract final answer
        answer_markers = ["FINAL ANSWER:", "ANSWER:", "Therefore:", "Thus:", "The answer is"]
        for marker in answer_markers:
            if marker in response:
                idx = response.find(marker)
                answer = response[idx + len(marker):].strip()
                # Take first line or sentence
                answer = answer.split("\n")[0].strip()
                answer = answer.split(".")[0].strip() if len(answer) > 200 else answer
                break

        if not answer:
            # Take last sentence as answer
            sentences = response.replace("\n", " ").split(".")
            answer = sentences[-1].strip() if sentences else response[:100]

        # Extract reasoning chain (numbered steps)
        step_pattern = r'(?:^|\n)\s*(\d+)[.)]\s*(.+?)(?=(?:\n\s*\d+[.)]|\n\n|$))'
        matches = re.findall(step_pattern, response, re.MULTILINE | re.DOTALL)
        chain = [m[1].strip() for m in matches]

        if not chain:
            # Split by newlines as fallback
            lines = [l.strip() for l in response.split("\n") if l.strip() and len(l.strip()) > 20]
            chain = lines[:5]

        return chain, answer

    def _estimate_confidence(self, response: str) -> float:
        """Estimate confidence from response text."""
        confidence = 0.7

        # Confidence boosters
        boosters = ["clearly", "definitely", "certainly", "must be", "obviously"]
        for word in boosters:
            if word in response.lower():
                confidence += 0.05

        # Confidence reducers
        reducers = ["maybe", "perhaps", "possibly", "might", "unsure", "unclear"]
        for word in reducers:
            if word in response.lower():
                confidence -= 0.05

        # Length and detail boost
        if len(response) > 500:
            confidence += 0.05

        return max(0.3, min(0.95, confidence))

    def _vote(self, paths: List[ReasoningPath]) -> ConsensusResult:
        """Vote on answers from multiple paths."""
        # Normalize answers if configured
        if self.config.normalize_answers:
            answers = [self._normalize_answer(p.final_answer) for p in paths]
        else:
            answers = [p.final_answer for p in paths]

        # Count votes
        vote_counts = Counter(answers)
        total_votes = len(paths)

        # Get winner
        if vote_counts:
            winning_answer, vote_count = vote_counts.most_common(1)[0]
            alternatives = vote_counts.most_common()[1:5]  # Top 4 alternatives
        else:
            winning_answer = paths[0].final_answer if paths else "No answer"
            vote_count = 1
            alternatives = []

        agreement_ratio = vote_count / total_votes if total_votes > 0 else 0

        # Find paths that voted for winner
        paths_used = [
            p.id for p, a in zip(paths, answers)
            if a == winning_answer
        ]

        return ConsensusResult(
            winning_answer=winning_answer,
            vote_count=vote_count,
            total_votes=total_votes,
            agreement_ratio=agreement_ratio,
            alternative_answers=alternatives,
            paths_used=paths_used
        )

    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison."""
        # Lowercase
        normalized = answer.lower().strip()

        # Remove common filler
        fillers = ["the answer is", "i think", "it's", "it is", "this is"]
        for filler in fillers:
            if normalized.startswith(filler):
                normalized = normalized[len(filler):].strip()

        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Collapse whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _build_trace(
        self,
        query: str,
        paths: List[ReasoningPath],
        consensus: ConsensusResult
    ) -> ThinkingTrace:
        """Build thinking trace from paths and consensus."""
        trace = ThinkingTrace(
            query=query,
            mode=ThinkingMode.CONSENSUS
        )

        # Add step for each path
        for path in paths:
            voted_for_winner = path.id in consensus.paths_used

            step = ThinkingStep(
                id=path.id,
                content=f"[{path.reasoning_style.upper()}]\n" +
                        "\n".join(f"  {i+1}. {s}" for i, s in enumerate(path.chain)) +
                        f"\n→ Answer: {path.final_answer}" +
                        f"\n{'✓ Agrees with consensus' if voted_for_winner else '✗ Disagrees'}",
                step_type="reasoning_path",
                confidence=path.confidence
            )
            trace.steps.append(step)

        # Add consensus step
        consensus_step = ThinkingStep(
            id="consensus",
            content=f"VOTING RESULT:\n" +
                    f"  Winner: {consensus.winning_answer}\n" +
                    f"  Votes: {consensus.vote_count}/{consensus.total_votes}\n" +
                    f"  Agreement: {consensus.agreement_ratio:.0%}\n" +
                    (f"  Alternatives: {consensus.alternative_answers}" if consensus.alternative_answers else ""),
            step_type="consensus",
            confidence=consensus.agreement_ratio
        )
        trace.steps.append(consensus_step)

        # Set final answer
        if consensus.agreement_ratio >= self.config.vote_threshold:
            trace.final_answer = consensus.winning_answer
            trace.confidence = consensus.agreement_ratio
        else:
            # Low agreement - report uncertainty
            trace.final_answer = f"[Low confidence] {consensus.winning_answer}"
            trace.confidence = consensus.agreement_ratio * 0.7

        return trace

    async def reason_with_debate(
        self,
        query: str,
        rounds: int = 2
    ) -> ThinkingTrace:
        """
        Enhanced self-consistency with debate rounds.

        Paths can see and respond to other paths' reasoning,
        potentially changing their answers.
        """
        # Initial round
        paths = await asyncio.gather(*[
            self._generate_path(query, i)
            for i in range(self.config.num_samples)
        ])

        llm = await self._get_llm()

        for round_num in range(rounds):
            logger.info(f"Debate round {round_num + 1}")

            # Each path sees others and can revise
            updated_paths = []
            for i, path in enumerate(paths):
                other_answers = [p.final_answer for j, p in enumerate(paths) if j != i]

                prompt = f"""You previously answered: {path.final_answer}

Other reasoners answered:
{chr(10).join(f'- {a}' for a in other_answers)}

ORIGINAL PROBLEM: {query}

Do you want to revise your answer after seeing others' responses?
If yes, explain why and give your new answer.
If no, explain why you're confident in your original answer.

REVISED ANSWER (or ORIGINAL if unchanged): [answer]"""

                response = await llm.generate(prompt, temperature=0.4)

                # Check if revised
                if "REVISED" in response or "change" in response.lower():
                    _, new_answer = self._parse_response(response)
                    path.final_answer = new_answer

                updated_paths.append(path)

            paths = updated_paths

        # Final vote
        consensus = self._vote(paths)
        return self._build_trace(query, paths, consensus)


# Global instance
_consistency_engine: Optional[SelfConsistency] = None


def get_consistency_engine(config: Optional[ConsistencyConfig] = None) -> SelfConsistency:
    """Get or create self-consistency instance."""
    global _consistency_engine
    if _consistency_engine is None or config is not None:
        _consistency_engine = SelfConsistency(config)
    return _consistency_engine


async def reason_consistent(query: str, **kwargs) -> ThinkingTrace:
    """Convenience function for self-consistent reasoning."""
    engine = get_consistency_engine()
    return await engine.reason(query, **kwargs)
