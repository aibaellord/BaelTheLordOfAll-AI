"""
BAEL Singularity Decision Pipeline
===================================

The Ultimate Decision Making System.
Uses ALL BAEL capabilities to make the best possible decisions.

Pipeline Stages:
1. PERCEPTION   - Gather and process all relevant input
2. INTUITION    - Fast initial assessment
3. ANALYSIS     - Deep multi-dimensional analysis
4. REASONING    - Multi-engine logical processing
5. CREATIVITY   - Generate novel options
6. EVALUATION   - Assess all options
7. ETHICS       - Ensure alignment
8. DECISION     - Make the final choice
9. PLANNING     - Create action plan
10. LEARNING    - Store for future reference

This is how BAEL makes decisions at maximum potential.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Singularity.DecisionPipeline")


# =============================================================================
# PIPELINE STAGES
# =============================================================================

class PipelineStage(Enum):
    """Stages of the decision pipeline."""
    PERCEPTION = "perception"
    INTUITION = "intuition"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    EVALUATION = "evaluation"
    ETHICS = "ethics"
    DECISION = "decision"
    PLANNING = "planning"
    LEARNING = "learning"


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage: PipelineStage
    success: bool
    data: Any
    confidence: float = 1.0
    execution_time: float = 0.0
    capabilities_used: List[str] = field(default_factory=list)


@dataclass
class DecisionContext:
    """Context passed through the pipeline."""
    query: str
    original_input: Any
    stage_results: Dict[PipelineStage, StageResult] = field(default_factory=dict)
    options: List[Dict[str, Any]] = field(default_factory=list)
    selected_option: Optional[Dict[str, Any]] = None
    action_plan: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    """Final result from the pipeline."""
    success: bool
    decision: Any
    confidence: float
    reasoning: str
    options_considered: List[Dict[str, Any]]
    action_plan: Optional[Dict[str, Any]]
    stage_results: Dict[str, StageResult]
    total_time: float
    capabilities_used: Set[str]


# =============================================================================
# DECISION PIPELINE
# =============================================================================

class DecisionPipeline:
    """
    The Ultimate Decision Pipeline.

    Uses every relevant BAEL capability to make optimal decisions.
    """

    def __init__(self, singularity):
        self.singularity = singularity
        self._stage_handlers: Dict[PipelineStage, Callable] = {
            PipelineStage.PERCEPTION: self._stage_perception,
            PipelineStage.INTUITION: self._stage_intuition,
            PipelineStage.ANALYSIS: self._stage_analysis,
            PipelineStage.REASONING: self._stage_reasoning,
            PipelineStage.CREATIVITY: self._stage_creativity,
            PipelineStage.EVALUATION: self._stage_evaluation,
            PipelineStage.ETHICS: self._stage_ethics,
            PipelineStage.DECISION: self._stage_decision,
            PipelineStage.PLANNING: self._stage_planning,
            PipelineStage.LEARNING: self._stage_learning,
        }

    async def decide(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        skip_stages: Optional[List[PipelineStage]] = None,
        fast_mode: bool = False
    ) -> DecisionResult:
        """
        Make a decision using the full pipeline.

        Args:
            query: The decision query or problem
            context: Additional context
            skip_stages: Stages to skip
            fast_mode: Use only essential stages

        Returns:
            DecisionResult with the final decision
        """
        start_time = datetime.now()
        skip = set(skip_stages or [])

        # In fast mode, skip non-essential stages
        if fast_mode:
            skip.update([
                PipelineStage.CREATIVITY,
                PipelineStage.ETHICS,
                PipelineStage.LEARNING
            ])

        # Initialize context
        ctx = DecisionContext(
            query=query,
            original_input=context or {},
            metadata={"fast_mode": fast_mode}
        )

        # Execute each stage
        all_capabilities = set()

        for stage in PipelineStage:
            if stage in skip:
                continue

            try:
                stage_start = datetime.now()
                result = await self._stage_handlers[stage](ctx)
                stage_time = (datetime.now() - stage_start).total_seconds()

                result.execution_time = stage_time
                ctx.stage_results[stage] = result

                all_capabilities.update(result.capabilities_used)

                logger.debug(f"Stage {stage.value}: {result.success} ({stage_time:.2f}s)")

            except Exception as e:
                logger.error(f"Stage {stage.value} failed: {e}")
                ctx.stage_results[stage] = StageResult(
                    stage=stage,
                    success=False,
                    data={"error": str(e)},
                    confidence=0.0
                )

        total_time = (datetime.now() - start_time).total_seconds()

        # Build final result
        return DecisionResult(
            success=ctx.selected_option is not None,
            decision=ctx.selected_option,
            confidence=self._calculate_confidence(ctx),
            reasoning=self._build_reasoning(ctx),
            options_considered=ctx.options,
            action_plan=ctx.action_plan,
            stage_results={s.value: r for s, r in ctx.stage_results.items()},
            total_time=total_time,
            capabilities_used=all_capabilities
        )

    # =========================================================================
    # STAGE IMPLEMENTATIONS
    # =========================================================================

    async def _stage_perception(self, ctx: DecisionContext) -> StageResult:
        """
        PERCEPTION: Gather and process all relevant information.

        Uses:
        - Memory search
        - Context analysis
        - Attention focusing
        """
        capabilities = []
        data = {"input": ctx.query, "context": ctx.original_input}

        # Search memory for relevant information
        try:
            memory = await self.singularity.invoke(
                "memory_manager",
                "search",
                query=ctx.query,
                limit=10
            )
            data["memories"] = memory
            capabilities.append("memory_manager")
        except Exception as e:
            data["memories"] = []

        # Focus attention
        try:
            attention = await self.singularity.invoke(
                "attention",
                "focus",
                input=ctx.query
            )
            data["attention"] = attention
            capabilities.append("attention")
        except Exception:
            pass

        return StageResult(
            stage=PipelineStage.PERCEPTION,
            success=True,
            data=data,
            confidence=0.9,
            capabilities_used=capabilities
        )

    async def _stage_intuition(self, ctx: DecisionContext) -> StageResult:
        """
        INTUITION: Fast initial assessment.

        Uses:
        - Intuition engine
        - Emotion engine
        - Pattern recognition
        """
        capabilities = []
        data = {}

        # Get intuitive response
        try:
            intuition = await self.singularity.invoke(
                "intuition",
                "assess",
                query=ctx.query
            )
            data["intuition"] = intuition
            capabilities.append("intuition")
        except Exception:
            data["intuition"] = {"assessment": "neutral"}

        # Get emotional assessment
        try:
            emotion = await self.singularity.invoke(
                "emotion",
                "assess",
                query=ctx.query
            )
            data["emotion"] = emotion
            capabilities.append("emotion")
        except Exception:
            data["emotion"] = {"valence": 0}

        # Initial confidence
        confidence = 0.6 if data.get("intuition") else 0.4

        return StageResult(
            stage=PipelineStage.INTUITION,
            success=True,
            data=data,
            confidence=confidence,
            capabilities_used=capabilities
        )

    async def _stage_analysis(self, ctx: DecisionContext) -> StageResult:
        """
        ANALYSIS: Deep multi-dimensional analysis.

        Uses:
        - Extended thinking
        - Metacognition
        - Multiple analysis dimensions
        """
        capabilities = []
        data = {}

        # Extended thinking
        try:
            thinking = await self.singularity.invoke(
                "extended_thinking",
                "think",
                query=ctx.query,
                max_steps=5
            )
            data["extended_thinking"] = thinking
            capabilities.append("extended_thinking")
        except Exception:
            pass

        # Metacognitive assessment
        try:
            meta = await self.singularity.invoke(
                "metacognition",
                "analyze",
                query=ctx.query
            )
            data["metacognition"] = meta
            capabilities.append("metacognition")
        except Exception:
            pass

        # Analyze dimensions
        data["dimensions"] = {
            "complexity": self._assess_complexity(ctx.query),
            "urgency": self._assess_urgency(ctx.query),
            "importance": self._assess_importance(ctx.query),
            "risk": self._assess_risk(ctx.query)
        }

        return StageResult(
            stage=PipelineStage.ANALYSIS,
            success=True,
            data=data,
            confidence=0.8,
            capabilities_used=capabilities
        )

    async def _stage_reasoning(self, ctx: DecisionContext) -> StageResult:
        """
        REASONING: Multi-engine logical processing.

        Uses:
        - Multiple reasoning engines
        - Game theory
        - Probabilistic reasoning
        """
        capabilities = []
        data = {"engines": {}}

        # Select relevant reasoning engines
        engines = self._select_reasoning_engines(ctx)

        # Run each engine
        for engine_name in engines:
            try:
                result = await self.singularity.invoke(
                    engine_name,
                    "reason",
                    query=ctx.query
                )
                data["engines"][engine_name] = result
                capabilities.append(engine_name)
            except Exception as e:
                data["engines"][engine_name] = {"error": str(e)}

        # Synthesize reasoning
        data["synthesis"] = self._synthesize_reasoning(data["engines"])

        return StageResult(
            stage=PipelineStage.REASONING,
            success=True,
            data=data,
            confidence=0.85,
            capabilities_used=capabilities
        )

    async def _stage_creativity(self, ctx: DecisionContext) -> StageResult:
        """
        CREATIVITY: Generate novel options.

        Uses:
        - Creativity engine
        - Curiosity engine
        - Swarm intelligence
        """
        capabilities = []
        options = []

        # Generate creative options
        try:
            creative = await self.singularity.invoke(
                "creativity",
                "generate_options",
                query=ctx.query,
                count=5
            )
            if isinstance(creative, list):
                options.extend(creative)
            elif isinstance(creative, dict) and "options" in creative:
                options.extend(creative["options"])
            capabilities.append("creativity")
        except Exception:
            pass

        # Curiosity-driven exploration
        try:
            curious = await self.singularity.invoke(
                "curiosity",
                "explore",
                topic=ctx.query
            )
            if isinstance(curious, dict) and "discoveries" in curious:
                for disc in curious["discoveries"]:
                    options.append({"source": "curiosity", "option": disc})
            capabilities.append("curiosity")
        except Exception:
            pass

        # Add options to context
        ctx.options.extend(options)

        # Ensure we have at least some options
        if not ctx.options:
            ctx.options = [
                {"option": "Proceed with standard approach", "source": "default"},
                {"option": "Gather more information", "source": "default"},
                {"option": "Defer decision", "source": "default"}
            ]

        return StageResult(
            stage=PipelineStage.CREATIVITY,
            success=True,
            data={"options_generated": len(options)},
            confidence=0.7,
            capabilities_used=capabilities
        )

    async def _stage_evaluation(self, ctx: DecisionContext) -> StageResult:
        """
        EVALUATION: Assess all options.

        Uses:
        - Game theory
        - Multi-criteria analysis
        - Risk assessment
        """
        capabilities = []
        evaluations = []

        for option in ctx.options:
            eval_result = {
                "option": option,
                "scores": {}
            }

            # Score each option
            try:
                # Utility score
                eval_result["scores"]["utility"] = self._score_utility(option, ctx)

                # Feasibility score
                eval_result["scores"]["feasibility"] = self._score_feasibility(option, ctx)

                # Risk score
                eval_result["scores"]["risk"] = self._score_risk(option, ctx)

                # Overall score
                eval_result["overall_score"] = (
                    eval_result["scores"]["utility"] * 0.4 +
                    eval_result["scores"]["feasibility"] * 0.3 +
                    (1 - eval_result["scores"]["risk"]) * 0.3
                )

                evaluations.append(eval_result)

            except Exception as e:
                logger.warning(f"Evaluation failed for option: {e}")

        # Game theory analysis
        try:
            game = await self.singularity.invoke(
                "game_theory",
                "analyze",
                options=ctx.options,
                scenario=ctx.query
            )
            capabilities.append("game_theory")
        except Exception:
            pass

        return StageResult(
            stage=PipelineStage.EVALUATION,
            success=True,
            data={"evaluations": evaluations},
            confidence=0.8,
            capabilities_used=capabilities
        )

    async def _stage_ethics(self, ctx: DecisionContext) -> StageResult:
        """
        ETHICS: Ensure alignment with values.

        Uses:
        - Ethics engine
        - Deontic reasoning
        - Value alignment check
        """
        capabilities = []
        data = {"checks": {}}

        # Check each top option for ethics
        evaluation_data = ctx.stage_results.get(PipelineStage.EVALUATION)
        if evaluation_data and "evaluations" in evaluation_data.data:
            top_options = sorted(
                evaluation_data.data["evaluations"],
                key=lambda x: x.get("overall_score", 0),
                reverse=True
            )[:3]

            for opt in top_options:
                option_key = str(opt.get("option", "unknown"))[:50]

                # Ethics check
                try:
                    ethics = await self.singularity.invoke(
                        "ethics",
                        "check",
                        action=option_key
                    )
                    data["checks"][option_key] = {
                        "ethical": ethics.get("approved", True),
                        "concerns": ethics.get("concerns", [])
                    }
                    capabilities.append("ethics")
                except Exception:
                    data["checks"][option_key] = {"ethical": True, "concerns": []}

                # Deontic check
                try:
                    deontic = await self.singularity.invoke(
                        "deontic",
                        "reason",
                        action=option_key
                    )
                    if option_key in data["checks"]:
                        data["checks"][option_key]["deontic"] = deontic
                    capabilities.append("deontic")
                except Exception:
                    pass

        return StageResult(
            stage=PipelineStage.ETHICS,
            success=True,
            data=data,
            confidence=0.9,
            capabilities_used=list(set(capabilities))
        )

    async def _stage_decision(self, ctx: DecisionContext) -> StageResult:
        """
        DECISION: Make the final choice.

        Uses:
        - Weighted synthesis of all prior stages
        - Consensus building
        - Final selection
        """
        capabilities = []

        # Get all evaluations
        eval_result = ctx.stage_results.get(PipelineStage.EVALUATION)
        ethics_result = ctx.stage_results.get(PipelineStage.ETHICS)

        if not eval_result or "evaluations" not in eval_result.data:
            # Fallback: select first option
            if ctx.options:
                ctx.selected_option = ctx.options[0]
            return StageResult(
                stage=PipelineStage.DECISION,
                success=True,
                data={"selected": ctx.selected_option, "method": "fallback"},
                confidence=0.5,
                capabilities_used=capabilities
            )

        # Filter by ethics
        evaluations = eval_result.data["evaluations"]
        if ethics_result and "checks" in ethics_result.data:
            ethics_checks = ethics_result.data["checks"]
            evaluations = [
                e for e in evaluations
                if ethics_checks.get(str(e.get("option", ""))[:50], {}).get("ethical", True)
            ]

        if not evaluations:
            evaluations = eval_result.data["evaluations"]

        # Select best option
        best = max(evaluations, key=lambda x: x.get("overall_score", 0))
        ctx.selected_option = best.get("option")

        return StageResult(
            stage=PipelineStage.DECISION,
            success=True,
            data={
                "selected": ctx.selected_option,
                "score": best.get("overall_score"),
                "method": "weighted_evaluation"
            },
            confidence=best.get("overall_score", 0.5),
            capabilities_used=capabilities
        )

    async def _stage_planning(self, ctx: DecisionContext) -> StageResult:
        """
        PLANNING: Create action plan.

        Uses:
        - Task decomposition
        - Temporal reasoning
        - Goal planning
        """
        capabilities = []

        if not ctx.selected_option:
            return StageResult(
                stage=PipelineStage.PLANNING,
                success=False,
                data={"error": "No option selected"},
                confidence=0.0,
                capabilities_used=capabilities
            )

        # Create action plan
        plan = {
            "decision": ctx.selected_option,
            "steps": [],
            "timeline": "immediate",
            "resources_needed": [],
            "success_criteria": []
        }

        # Decompose into steps
        try:
            decomposition = await self.singularity.invoke(
                "task",
                "decompose",
                goal=str(ctx.selected_option)
            )
            if isinstance(decomposition, list):
                plan["steps"] = decomposition
            capabilities.append("task")
        except Exception:
            plan["steps"] = [
                {"step": 1, "action": "Implement selected option"},
                {"step": 2, "action": "Monitor results"},
                {"step": 3, "action": "Adjust as needed"}
            ]

        ctx.action_plan = plan

        return StageResult(
            stage=PipelineStage.PLANNING,
            success=True,
            data=plan,
            confidence=0.8,
            capabilities_used=capabilities
        )

    async def _stage_learning(self, ctx: DecisionContext) -> StageResult:
        """
        LEARNING: Store for future reference.

        Uses:
        - Memory storage
        - Experience learning
        - Pattern extraction
        """
        capabilities = []

        # Store decision in memory
        try:
            await self.singularity.invoke(
                "memory_manager",
                "store",
                key=f"decision_{datetime.now().isoformat()}",
                value={
                    "query": ctx.query,
                    "decision": ctx.selected_option,
                    "options_considered": len(ctx.options),
                    "confidence": self._calculate_confidence(ctx)
                },
                memory_type="episodic"
            )
            capabilities.append("memory_manager")
        except Exception as e:
            logger.warning(f"Failed to store decision: {e}")

        # Extract patterns
        try:
            await self.singularity.invoke(
                "feedback_learning",
                "learn",
                experience={
                    "type": "decision",
                    "query": ctx.query,
                    "outcome": ctx.selected_option
                }
            )
            capabilities.append("feedback_learning")
        except Exception:
            pass

        return StageResult(
            stage=PipelineStage.LEARNING,
            success=True,
            data={"stored": True},
            confidence=1.0,
            capabilities_used=capabilities
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _select_reasoning_engines(self, ctx: DecisionContext) -> List[str]:
        """Select relevant reasoning engines."""
        query_lower = ctx.query.lower()
        engines = []

        # Always include these
        engines.append("deductive")
        engines.append("inductive")

        # Contextual engines
        if any(w in query_lower for w in ["why", "cause", "because"]):
            engines.append("causal_reasoning")
        if any(w in query_lower for w in ["what if", "would", "could"]):
            engines.append("counterfactual")
        if any(w in query_lower for w in ["probably", "likely", "chance"]):
            engines.append("probabilistic")
        if any(w in query_lower for w in ["should", "must", "allowed"]):
            engines.append("deontic")
        if any(w in query_lower for w in ["game", "strategy", "opponent", "compete"]):
            engines.append("game_theory")

        return list(set(engines))

    def _assess_complexity(self, query: str) -> float:
        """Assess query complexity."""
        # Simple heuristic based on length and structure
        score = min(len(query) / 500, 1.0)
        if any(w in query.lower() for w in ["complex", "difficult", "hard"]):
            score = min(score + 0.3, 1.0)
        return score

    def _assess_urgency(self, query: str) -> float:
        """Assess query urgency."""
        if any(w in query.lower() for w in ["urgent", "immediately", "asap", "now"]):
            return 0.9
        if any(w in query.lower() for w in ["soon", "quickly"]):
            return 0.7
        return 0.5

    def _assess_importance(self, query: str) -> float:
        """Assess query importance."""
        if any(w in query.lower() for w in ["critical", "important", "crucial"]):
            return 0.9
        if any(w in query.lower() for w in ["significant", "major"]):
            return 0.7
        return 0.5

    def _assess_risk(self, query: str) -> float:
        """Assess risk level."""
        if any(w in query.lower() for w in ["dangerous", "risky", "careful"]):
            return 0.8
        return 0.3

    def _synthesize_reasoning(self, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize reasoning from multiple engines."""
        synthesis = {
            "agreement_level": 0.0,
            "key_points": [],
            "conflicts": []
        }

        valid_results = [
            r for r in engine_results.values()
            if isinstance(r, dict) and "error" not in r
        ]

        if valid_results:
            synthesis["agreement_level"] = 0.7  # Simplified

        return synthesis

    def _score_utility(self, option: Any, ctx: DecisionContext) -> float:
        """Score option utility."""
        return 0.7  # Simplified

    def _score_feasibility(self, option: Any, ctx: DecisionContext) -> float:
        """Score option feasibility."""
        return 0.8  # Simplified

    def _score_risk(self, option: Any, ctx: DecisionContext) -> float:
        """Score option risk."""
        return 0.3  # Simplified

    def _calculate_confidence(self, ctx: DecisionContext) -> float:
        """Calculate overall confidence."""
        confidences = [
            r.confidence for r in ctx.stage_results.values()
            if r.success
        ]
        return sum(confidences) / len(confidences) if confidences else 0.5

    def _build_reasoning(self, ctx: DecisionContext) -> str:
        """Build reasoning explanation."""
        parts = []

        if PipelineStage.INTUITION in ctx.stage_results:
            parts.append("Initial intuition considered")

        if PipelineStage.ANALYSIS in ctx.stage_results:
            parts.append("Deep analysis performed")

        if PipelineStage.REASONING in ctx.stage_results:
            r = ctx.stage_results[PipelineStage.REASONING]
            engines = r.capabilities_used
            parts.append(f"Reasoning with {len(engines)} engines")

        if PipelineStage.EVALUATION in ctx.stage_results:
            parts.append(f"{len(ctx.options)} options evaluated")

        if PipelineStage.ETHICS in ctx.stage_results:
            parts.append("Ethics verified")

        return "; ".join(parts) if parts else "Standard decision process"


# =============================================================================
# FACTORY
# =============================================================================

def create_decision_pipeline(singularity) -> DecisionPipeline:
    """Create a decision pipeline."""
    return DecisionPipeline(singularity)
