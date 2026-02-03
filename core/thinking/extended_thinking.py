"""
BAEL - Extended Thinking Engine
Deep multi-step reasoning with visible thinking tokens.
Implements o1/Claude-style extended thinking for complex problems.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from . import (ThinkingConfig, ThinkingDepth, ThinkingMode, ThinkingStep,
               ThinkingTrace)

logger = logging.getLogger("BAEL.Thinking.Extended")


class ReasoningPhase(Enum):
    """Phases of extended reasoning."""
    UNDERSTAND = "understand"
    DECOMPOSE = "decompose"
    ANALYZE = "analyze"
    SYNTHESIZE = "synthesize"
    VERIFY = "verify"
    REFLECT = "reflect"


@dataclass
class ThinkingContext:
    """Context maintained during thinking."""
    original_query: str
    current_focus: str
    hypotheses: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    confidence_history: List[float] = field(default_factory=list)


class ExtendedThinker:
    """
    Extended Thinking Engine for deep reasoning.

    Features:
    - Multi-step reasoning with explicit thinking tokens
    - Self-reflection and verification loops
    - Confidence tracking and uncertainty handling
    - Streaming thinking output
    - Automatic depth adjustment based on problem complexity
    """

    def __init__(self, config: Optional[ThinkingConfig] = None):
        self.config = config or ThinkingConfig()
        self._llm = None

        # Thinking prompts
        self._phase_prompts = {
            ReasoningPhase.UNDERSTAND: self._understand_prompt,
            ReasoningPhase.DECOMPOSE: self._decompose_prompt,
            ReasoningPhase.ANALYZE: self._analyze_prompt,
            ReasoningPhase.SYNTHESIZE: self._synthesize_prompt,
            ReasoningPhase.VERIFY: self._verify_prompt,
            ReasoningPhase.REFLECT: self._reflect_prompt,
        }

    async def _get_llm(self):
        """Lazy load LLM provider."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                logger.warning("LLM provider not available, using mock")
                self._llm = MockLLM()
        return self._llm

    async def think(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> ThinkingTrace:
        """
        Perform extended thinking on a query.

        Args:
            query: The problem or question to think about
            context: Additional context (memory, history, etc.)
            stream: Whether to stream thinking steps

        Returns:
            ThinkingTrace with complete reasoning process
        """
        start_time = datetime.now()
        trace = ThinkingTrace(
            query=query,
            mode=self.config.mode
        )

        thinking_context = ThinkingContext(
            original_query=query,
            current_focus=query
        )

        # Determine complexity and adjust depth
        complexity = await self._assess_complexity(query)
        self._adjust_depth(complexity)

        logger.info(f"Starting extended thinking (complexity: {complexity}, depth: {self.config.depth})")

        # Phase 1: Understand the problem
        understand_step = await self._execute_phase(
            ReasoningPhase.UNDERSTAND,
            thinking_context,
            trace
        )
        trace.steps.append(understand_step)

        # Phase 2: Decompose into sub-problems
        decompose_step = await self._execute_phase(
            ReasoningPhase.DECOMPOSE,
            thinking_context,
            trace
        )
        trace.steps.append(decompose_step)

        # Phase 3: Analyze each component (iterative)
        sub_problems = self._extract_subproblems(decompose_step.content)
        for i, sub_problem in enumerate(sub_problems[:self.config.max_steps - 4]):
            thinking_context.current_focus = sub_problem
            analyze_step = await self._execute_phase(
                ReasoningPhase.ANALYZE,
                thinking_context,
                trace
            )
            analyze_step.id = f"analyze_{i}"
            trace.steps.append(analyze_step)

            # Extract insights
            insight = self._extract_insight(analyze_step.content)
            if insight:
                thinking_context.insights.append(insight)

        # Phase 4: Synthesize findings
        thinking_context.current_focus = query
        synthesize_step = await self._execute_phase(
            ReasoningPhase.SYNTHESIZE,
            thinking_context,
            trace
        )
        trace.steps.append(synthesize_step)

        # Phase 5: Verify conclusion
        verify_step = await self._execute_phase(
            ReasoningPhase.VERIFY,
            thinking_context,
            trace
        )
        trace.steps.append(verify_step)

        # Phase 6: Reflect (if enabled and needed)
        if self.config.reflection_enabled and verify_step.confidence < 0.8:
            reflect_step = await self._execute_phase(
                ReasoningPhase.REFLECT,
                thinking_context,
                trace
            )
            trace.steps.append(reflect_step)

            # May trigger additional analysis
            if "reconsider" in reflect_step.content.lower():
                await self._iterative_refinement(thinking_context, trace)

        # Extract final answer
        trace.final_answer = await self._formulate_answer(thinking_context, trace)
        trace.confidence = self._calculate_confidence(trace)
        trace.thinking_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"Extended thinking complete: {len(trace.steps)} steps, confidence: {trace.confidence:.2f}")

        return trace

    async def think_stream(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ThinkingStep, None]:
        """
        Stream thinking steps as they occur.

        Yields:
            ThinkingStep objects as reasoning progresses
        """
        thinking_context = ThinkingContext(
            original_query=query,
            current_focus=query
        )

        # Stream each phase
        for phase in ReasoningPhase:
            step = await self._execute_phase(
                phase,
                thinking_context,
                None  # No trace accumulation in streaming mode
            )
            yield step

            if phase == ReasoningPhase.VERIFY and step.confidence >= 0.85:
                break  # High confidence, no need for reflection

    async def _execute_phase(
        self,
        phase: ReasoningPhase,
        context: ThinkingContext,
        trace: Optional[ThinkingTrace]
    ) -> ThinkingStep:
        """Execute a single reasoning phase."""
        prompt = self._phase_prompts[phase](context, trace)

        llm = await self._get_llm()
        response = await llm.generate(prompt, temperature=self.config.temperature)

        step = ThinkingStep(
            id=f"{phase.value}_{uuid.uuid4().hex[:8]}",
            content=response,
            step_type=phase.value,
            confidence=self._estimate_step_confidence(response)
        )

        context.confidence_history.append(step.confidence)

        return step

    async def _assess_complexity(self, query: str) -> float:
        """Assess the complexity of a query (0-1 scale)."""
        # Heuristic complexity assessment
        complexity = 0.5

        # Length factor
        if len(query) > 500:
            complexity += 0.1
        if len(query) > 1000:
            complexity += 0.1

        # Question complexity indicators
        complex_indicators = [
            "why", "how", "explain", "analyze", "compare",
            "evaluate", "synthesize", "design", "optimize",
            "prove", "derive", "implications"
        ]
        for indicator in complex_indicators:
            if indicator in query.lower():
                complexity += 0.05

        # Multi-part questions
        if "and" in query or "?" in query[:-1]:
            complexity += 0.1

        return min(complexity, 1.0)

    def _adjust_depth(self, complexity: float) -> None:
        """Adjust thinking depth based on complexity."""
        if complexity < 0.3:
            self.config.depth = ThinkingDepth.SHALLOW
            self.config.max_steps = 5
        elif complexity < 0.5:
            self.config.depth = ThinkingDepth.MODERATE
            self.config.max_steps = 10
        elif complexity < 0.7:
            self.config.depth = ThinkingDepth.DEEP
            self.config.max_steps = 15
        else:
            self.config.depth = ThinkingDepth.EXHAUSTIVE
            self.config.max_steps = 25

    def _extract_subproblems(self, decomposition: str) -> List[str]:
        """Extract sub-problems from decomposition step."""
        # Parse numbered or bulleted lists
        lines = decomposition.split("\n")
        subproblems = []

        for line in lines:
            line = line.strip()
            if line and (
                line[0].isdigit() or
                line.startswith("-") or
                line.startswith("•") or
                line.startswith("*")
            ):
                # Clean up the line
                clean = line.lstrip("0123456789.-•* ")
                if len(clean) > 10:  # Meaningful sub-problem
                    subproblems.append(clean)

        return subproblems if subproblems else [decomposition[:200]]

    def _extract_insight(self, analysis: str) -> Optional[str]:
        """Extract key insight from analysis."""
        # Look for insight markers
        markers = ["therefore", "thus", "key insight", "importantly", "notably", "conclusion"]

        for marker in markers:
            if marker in analysis.lower():
                idx = analysis.lower().find(marker)
                # Extract sentence containing the marker
                start = analysis.rfind(".", 0, idx) + 1
                end = analysis.find(".", idx)
                if end == -1:
                    end = len(analysis)
                return analysis[start:end].strip()

        # Fallback: last sentence
        sentences = analysis.split(".")
        if sentences:
            return sentences[-2].strip() if len(sentences) > 1 else sentences[-1].strip()

        return None

    async def _iterative_refinement(
        self,
        context: ThinkingContext,
        trace: ThinkingTrace
    ) -> None:
        """Perform iterative refinement when confidence is low."""
        logger.info("Performing iterative refinement...")

        # Re-analyze with different focus
        for insight in context.insights[-3:]:  # Focus on recent insights
            context.current_focus = f"Reconsidering: {insight}"
            refine_step = await self._execute_phase(
                ReasoningPhase.ANALYZE,
                context,
                trace
            )
            refine_step.id = f"refine_{uuid.uuid4().hex[:6]}"
            trace.steps.append(refine_step)

    async def _formulate_answer(
        self,
        context: ThinkingContext,
        trace: ThinkingTrace
    ) -> str:
        """Formulate final answer from thinking trace."""
        llm = await self._get_llm()

        # Compile insights
        insights_text = "\n".join(f"- {i}" for i in context.insights)

        prompt = f"""Based on the following extended thinking process, formulate a clear and comprehensive answer.

Original Question: {context.original_query}

Key Insights Discovered:
{insights_text}

Synthesis Step:
{trace.steps[-2].content if len(trace.steps) >= 2 else "N/A"}

Verification:
{trace.steps[-1].content if trace.steps else "N/A"}

Provide a clear, well-structured answer that addresses the original question completely."""

        return await llm.generate(prompt, temperature=0.3)

    def _estimate_step_confidence(self, content: str) -> float:
        """Estimate confidence of a thinking step."""
        confidence = 0.7  # Base confidence

        # Uncertainty indicators (reduce confidence)
        uncertainty = ["maybe", "perhaps", "possibly", "unclear", "uncertain", "not sure"]
        for word in uncertainty:
            if word in content.lower():
                confidence -= 0.05

        # Confidence indicators (increase confidence)
        certainty = ["clearly", "definitely", "certainly", "proven", "established", "evidence shows"]
        for word in certainty:
            if word in content.lower():
                confidence += 0.05

        # Length and detail (moderate confidence boost)
        if len(content) > 500:
            confidence += 0.05

        return max(0.1, min(0.95, confidence))

    def _calculate_confidence(self, trace: ThinkingTrace) -> float:
        """Calculate overall confidence from trace."""
        if not trace.steps:
            return 0.5

        # Weighted average with more weight on later steps
        weights = [i + 1 for i in range(len(trace.steps))]
        weighted_sum = sum(
            step.confidence * w
            for step, w in zip(trace.steps, weights)
        )

        return weighted_sum / sum(weights)

    # Phase prompt generators
    def _understand_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        return f"""<thinking>
I need to deeply understand this problem before attempting to solve it.

PROBLEM: {ctx.original_query}

Let me break down what is being asked:
1. What is the core question or task?
2. What are the key concepts involved?
3. What information do I have vs. what do I need?
4. What are the constraints or requirements?
5. What would a successful answer look like?

My understanding:
</thinking>"""

    def _decompose_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        prev_understanding = trace.steps[-1].content if trace and trace.steps else "N/A"
        return f"""<thinking>
Based on my understanding, I need to break this problem into manageable sub-problems.

ORIGINAL PROBLEM: {ctx.original_query}

MY UNDERSTANDING: {prev_understanding[:500]}

Sub-problems to solve:
1.
2.
3.
(continue as needed)

For each sub-problem, I'll identify:
- What needs to be determined
- What approach to use
- What challenges might arise
</thinking>"""

    def _analyze_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        return f"""<thinking>
Now I'm analyzing this specific aspect:

FOCUS: {ctx.current_focus}

CONTEXT FROM ORIGINAL PROBLEM: {ctx.original_query[:200]}

My analysis:
- Key observations:
- Relevant patterns or principles:
- Potential approaches:
- Evidence and reasoning:

My conclusion for this aspect:
</thinking>"""

    def _synthesize_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        insights_text = "\n".join(f"- {i}" for i in ctx.insights[-5:])
        return f"""<thinking>
Now I need to synthesize all my findings into a coherent answer.

ORIGINAL QUESTION: {ctx.original_query}

KEY INSIGHTS DISCOVERED:
{insights_text}

Synthesizing these findings:
- How do they connect?
- What overall pattern emerges?
- What is the complete answer?

My synthesized conclusion:
</thinking>"""

    def _verify_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        synthesis = trace.steps[-1].content if trace and trace.steps else "N/A"
        return f"""<thinking>
I need to verify my conclusion is correct and complete.

MY CONCLUSION: {synthesis[:500]}

Verification checklist:
1. Does this directly answer the original question?
2. Is the logic sound and free of errors?
3. Have I considered alternative interpretations?
4. Are there any gaps or missing considerations?
5. Would this answer be useful and actionable?

Verification result:
</thinking>"""

    def _reflect_prompt(self, ctx: ThinkingContext, trace: Optional[ThinkingTrace]) -> str:
        conf_history = ctx.confidence_history[-5:] if ctx.confidence_history else []
        return f"""<thinking>
My confidence has been variable. Let me reflect on my reasoning process.

CONFIDENCE HISTORY: {conf_history}

Reflection questions:
1. Where was I most uncertain and why?
2. What assumptions did I make?
3. Could I have reasoned differently?
4. What would strengthen my conclusion?
5. Should I reconsider any aspect?

My reflection:
</thinking>"""


class MockLLM:
    """Mock LLM for testing without API."""

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        # Return structured mock response based on prompt content
        if "understand" in prompt.lower():
            return "Understanding: This is a complex problem requiring careful analysis of multiple factors. The core question involves determining the optimal approach given the constraints. Key concepts include logical reasoning, evidence evaluation, and systematic problem-solving."
        elif "decompose" in prompt.lower():
            return "1. First, we need to identify the key variables\n2. Second, analyze the relationships between them\n3. Third, evaluate potential solutions\n4. Finally, synthesize into a coherent answer"
        elif "analyze" in prompt.lower():
            return "Analysis reveals several important patterns. The evidence suggests a clear relationship between the variables. Key insight: the solution requires balancing multiple competing factors."
        elif "synthesize" in prompt.lower():
            return "Synthesizing all findings: The complete answer integrates the insights from each sub-analysis. The pattern that emerges shows a clear path forward."
        elif "verify" in prompt.lower():
            return "Verification complete: The conclusion directly addresses the original question. Logic is sound. No significant gaps identified. Confidence: high."
        elif "reflect" in prompt.lower():
            return "Reflection: The reasoning process was thorough. Assumptions were reasonable. The conclusion is well-supported by the analysis."
        else:
            return "Extended thinking complete. The analysis reveals a comprehensive understanding of the problem and its solution."


# Global instance
_extended_thinker: Optional[ExtendedThinker] = None


def get_extended_thinker(config: Optional[ThinkingConfig] = None) -> ExtendedThinker:
    """Get or create the extended thinker instance."""
    global _extended_thinker
    if _extended_thinker is None or config is not None:
        _extended_thinker = ExtendedThinker(config)
    return _extended_thinker


async def think_deeply(query: str, **kwargs) -> ThinkingTrace:
    """Convenience function for extended thinking."""
    thinker = get_extended_thinker()
    return await thinker.think(query, **kwargs)
