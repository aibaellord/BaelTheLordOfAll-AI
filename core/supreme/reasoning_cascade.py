"""
BAEL Reasoning Cascade - Intelligent Reasoning Engine Orchestration

The Reasoning Cascade intelligently routes queries to the appropriate
reasoning engines from BAEL's 25+ reasoning modalities:

FORMAL LOGIC:
- Deductive: Classical logical inference
- Inductive: Pattern-to-rule generalization
- Abductive: Inference to best explanation

CAUSAL/TEMPORAL:
- Causal: Do-calculus, SCMs, interventions
- Counterfactual: What-if analysis
- Temporal: Allen's interval algebra

EPISTEMIC/DEONTIC:
- Epistemic: Knowledge, belief, justification
- Deontic: Obligation, permission, prohibition
- Defeasible: Non-monotonic reasoning

NON-CLASSICAL:
- Paraconsistent: Reasoning with contradictions
- Fuzzy: Degrees of truth
- Probabilistic: Bayesian inference
- Modal: Possibility, necessity

COGNITIVE:
- Analogical: Cross-domain mapping
- Commonsense: Scripts, frames, defaults
- Case-based: Prior cases as knowledge

STRATEGIC:
- Game theory: Nash equilibrium, mechanism design
- Argumentation: Dung's frameworks
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.ReasoningCascade")


class ReasoningMode(Enum):
    """Modes for reasoning execution."""
    SINGLE = "single"          # Use best-matching reasoner
    CASCADE = "cascade"        # Try in sequence until success
    PARALLEL = "parallel"      # Run multiple in parallel
    ENSEMBLE = "ensemble"      # Combine multiple outputs
    DELIBERATIVE = "deliberative"  # Full council deliberation


class ReasonerType(Enum):
    """All available reasoning engine types."""
    # Formal Logic
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"

    # Causal/Temporal
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"
    TEMPORAL = "temporal"

    # Epistemic/Normative
    EPISTEMIC = "epistemic"
    DEONTIC = "deontic"
    DEFEASIBLE = "defeasible"

    # Non-Classical
    PARACONSISTENT = "paraconsistent"
    FUZZY = "fuzzy"
    PROBABILISTIC = "probabilistic"
    MODAL = "modal"

    # Cognitive
    ANALOGICAL = "analogical"
    COMMONSENSE = "commonsense"
    CASEBASED = "casebased"
    QUALITATIVE = "qualitative"
    SPATIAL = "spatial"

    # Strategic
    GAMETHEORY = "gametheory"
    ARGUMENTATION = "argumentation"
    GRAPHREASON = "graphreason"


@dataclass
class ReasonerCapability:
    """Capability profile of a reasoning engine."""
    reasoner_type: ReasonerType
    strength_domains: List[str]  # Domains where this reasoner excels
    weakness_domains: List[str]  # Domains where this reasoner struggles
    average_latency_ms: float
    success_rate: float  # Historical success rate
    confidence_calibration: float  # How well-calibrated confidence is
    complexity_threshold: float  # Max complexity it handles well
    requires_knowledge: bool  # Whether it needs knowledge base
    supports_uncertainty: bool  # Whether it handles uncertainty


@dataclass
class ReasoningRequest:
    """Request for reasoning."""
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    required_reasoners: List[ReasonerType] = field(default_factory=list)
    excluded_reasoners: List[ReasonerType] = field(default_factory=list)
    mode: ReasoningMode = ReasoningMode.SINGLE
    max_latency_ms: float = 5000
    min_confidence: float = 0.5
    require_explanation: bool = True


@dataclass
class ReasoningStep:
    """Single step in a reasoning chain."""
    reasoner: ReasonerType
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    latency_ms: float
    explanation: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningResult:
    """Result of reasoning cascade."""
    success: bool
    final_answer: Any
    confidence: float
    chain: List[ReasoningStep]
    reasoners_used: List[ReasonerType]
    total_latency_ms: float
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReasonerRegistry:
    """Registry of all available reasoning engines."""

    # Define capabilities for each reasoner
    CAPABILITIES = {
        ReasonerType.DEDUCTIVE: ReasonerCapability(
            reasoner_type=ReasonerType.DEDUCTIVE,
            strength_domains=["logic", "proofs", "verification", "formal"],
            weakness_domains=["uncertainty", "creativity", "analogies"],
            average_latency_ms=50,
            success_rate=0.95,
            confidence_calibration=0.9,
            complexity_threshold=0.8,
            requires_knowledge=True,
            supports_uncertainty=False
        ),
        ReasonerType.INDUCTIVE: ReasonerCapability(
            reasoner_type=ReasonerType.INDUCTIVE,
            strength_domains=["patterns", "generalization", "learning"],
            weakness_domains=["rare events", "exceptions"],
            average_latency_ms=100,
            success_rate=0.8,
            confidence_calibration=0.7,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.ABDUCTIVE: ReasonerCapability(
            reasoner_type=ReasonerType.ABDUCTIVE,
            strength_domains=["diagnosis", "explanation", "hypothesis"],
            weakness_domains=["proof", "certainty"],
            average_latency_ms=150,
            success_rate=0.75,
            confidence_calibration=0.65,
            complexity_threshold=0.6,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.CAUSAL: ReasonerCapability(
            reasoner_type=ReasonerType.CAUSAL,
            strength_domains=["causation", "intervention", "effects"],
            weakness_domains=["correlation-only data"],
            average_latency_ms=200,
            success_rate=0.85,
            confidence_calibration=0.8,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.COUNTERFACTUAL: ReasonerCapability(
            reasoner_type=ReasonerType.COUNTERFACTUAL,
            strength_domains=["what-if", "alternatives", "regret"],
            weakness_domains=["factual queries"],
            average_latency_ms=250,
            success_rate=0.8,
            confidence_calibration=0.7,
            complexity_threshold=0.6,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.TEMPORAL: ReasonerCapability(
            reasoner_type=ReasonerType.TEMPORAL,
            strength_domains=["time", "sequences", "scheduling", "history"],
            weakness_domains=["atemporal facts"],
            average_latency_ms=100,
            success_rate=0.9,
            confidence_calibration=0.85,
            complexity_threshold=0.8,
            requires_knowledge=True,
            supports_uncertainty=False
        ),
        ReasonerType.EPISTEMIC: ReasonerCapability(
            reasoner_type=ReasonerType.EPISTEMIC,
            strength_domains=["knowledge", "belief", "justification"],
            weakness_domains=["action planning"],
            average_latency_ms=120,
            success_rate=0.85,
            confidence_calibration=0.8,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.DEONTIC: ReasonerCapability(
            reasoner_type=ReasonerType.DEONTIC,
            strength_domains=["obligation", "permission", "norms", "ethics"],
            weakness_domains=["descriptive facts"],
            average_latency_ms=100,
            success_rate=0.9,
            confidence_calibration=0.85,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=False
        ),
        ReasonerType.DEFEASIBLE: ReasonerCapability(
            reasoner_type=ReasonerType.DEFEASIBLE,
            strength_domains=["exceptions", "defaults", "retraction"],
            weakness_domains=["monotonic proofs"],
            average_latency_ms=150,
            success_rate=0.85,
            confidence_calibration=0.75,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.PARACONSISTENT: ReasonerCapability(
            reasoner_type=ReasonerType.PARACONSISTENT,
            strength_domains=["contradictions", "inconsistency", "partial truth"],
            weakness_domains=["classical consistency"],
            average_latency_ms=180,
            success_rate=0.8,
            confidence_calibration=0.7,
            complexity_threshold=0.6,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.FUZZY: ReasonerCapability(
            reasoner_type=ReasonerType.FUZZY,
            strength_domains=["vague concepts", "degrees", "approximation"],
            weakness_domains=["precise values"],
            average_latency_ms=80,
            success_rate=0.9,
            confidence_calibration=0.85,
            complexity_threshold=0.8,
            requires_knowledge=False,
            supports_uncertainty=True
        ),
        ReasonerType.PROBABILISTIC: ReasonerCapability(
            reasoner_type=ReasonerType.PROBABILISTIC,
            strength_domains=["uncertainty", "likelihood", "bayesian"],
            weakness_domains=["certainty", "proofs"],
            average_latency_ms=120,
            success_rate=0.85,
            confidence_calibration=0.9,
            complexity_threshold=0.7,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.ANALOGICAL: ReasonerCapability(
            reasoner_type=ReasonerType.ANALOGICAL,
            strength_domains=["transfer", "similarity", "creativity"],
            weakness_domains=["precision", "proofs"],
            average_latency_ms=200,
            success_rate=0.7,
            confidence_calibration=0.6,
            complexity_threshold=0.5,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.COMMONSENSE: ReasonerCapability(
            reasoner_type=ReasonerType.COMMONSENSE,
            strength_domains=["everyday", "defaults", "scripts"],
            weakness_domains=["formal domains", "technical"],
            average_latency_ms=100,
            success_rate=0.85,
            confidence_calibration=0.75,
            complexity_threshold=0.6,
            requires_knowledge=True,
            supports_uncertainty=True
        ),
        ReasonerType.GAMETHEORY: ReasonerCapability(
            reasoner_type=ReasonerType.GAMETHEORY,
            strength_domains=["strategy", "competition", "negotiation"],
            weakness_domains=["cooperation", "single-agent"],
            average_latency_ms=300,
            success_rate=0.8,
            confidence_calibration=0.85,
            complexity_threshold=0.7,
            requires_knowledge=False,
            supports_uncertainty=True
        ),
    }

    def get_capability(self, reasoner_type: ReasonerType) -> Optional[ReasonerCapability]:
        """Get capability profile for a reasoner."""
        return self.CAPABILITIES.get(reasoner_type)

    def get_best_for_domain(self, domain: str) -> List[ReasonerType]:
        """Get reasoners best suited for a domain."""
        matches = []
        for rtype, cap in self.CAPABILITIES.items():
            if domain.lower() in [d.lower() for d in cap.strength_domains]:
                matches.append((rtype, cap.success_rate))

        # Sort by success rate
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]


class ReasoningCascade:
    """
    Intelligent orchestrator for BAEL's 25+ reasoning engines.

    The cascade:
    1. Analyzes the query to determine required reasoning types
    2. Selects optimal reasoners based on capability profiles
    3. Executes reasoning in the configured mode (single/cascade/parallel/ensemble)
    4. Combines results and generates comprehensive explanation
    """

    def __init__(self):
        self.registry = ReasonerRegistry()
        self._reasoner_instances: Dict[ReasonerType, Any] = {}
        self._metrics: Dict[ReasonerType, Dict[str, float]] = {}

        # Initialize metrics for each reasoner
        for rtype in ReasonerType:
            self._metrics[rtype] = {
                "invocations": 0,
                "successes": 0,
                "total_latency_ms": 0,
                "average_confidence": 0
            }

    async def initialize(self) -> None:
        """Initialize all reasoning engines."""
        logger.info("Initializing Reasoning Cascade...")

        for rtype in ReasonerType:
            try:
                # In production, would dynamically import reasoner modules
                self._reasoner_instances[rtype] = {
                    "type": rtype,
                    "status": "ready",
                    "module_path": f"core.{rtype.value}"
                }
            except Exception as e:
                logger.warning(f"Failed to load reasoner {rtype.value}: {e}")

        logger.info(f"Initialized {len(self._reasoner_instances)} reasoning engines")

    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Execute reasoning based on the request configuration."""
        start_time = datetime.now()

        # Select reasoners
        reasoners = self._select_reasoners(request)

        if not reasoners:
            return ReasoningResult(
                success=False,
                final_answer=None,
                confidence=0,
                chain=[],
                reasoners_used=[],
                total_latency_ms=self._elapsed_ms(start_time),
                explanation="No suitable reasoners found for this query"
            )

        # Execute based on mode
        if request.mode == ReasoningMode.SINGLE:
            result = await self._execute_single(request, reasoners[0])
        elif request.mode == ReasoningMode.CASCADE:
            result = await self._execute_cascade(request, reasoners)
        elif request.mode == ReasoningMode.PARALLEL:
            result = await self._execute_parallel(request, reasoners)
        elif request.mode == ReasoningMode.ENSEMBLE:
            result = await self._execute_ensemble(request, reasoners)
        else:
            result = await self._execute_single(request, reasoners[0])

        result.total_latency_ms = self._elapsed_ms(start_time)
        return result

    def _select_reasoners(self, request: ReasoningRequest) -> List[ReasonerType]:
        """Select appropriate reasoners for the request."""
        if request.required_reasoners:
            # Use specified reasoners
            return [r for r in request.required_reasoners if r not in request.excluded_reasoners]

        # Auto-select based on query analysis
        selected = []
        query_lower = request.query.lower()

        # Domain detection patterns
        domain_patterns = {
            "cause": [ReasonerType.CAUSAL, ReasonerType.COUNTERFACTUAL],
            "why": [ReasonerType.CAUSAL, ReasonerType.ABDUCTIVE],
            "what if": [ReasonerType.COUNTERFACTUAL],
            "should": [ReasonerType.DEONTIC, ReasonerType.EPISTEMIC],
            "must": [ReasonerType.DEONTIC],
            "when": [ReasonerType.TEMPORAL],
            "before": [ReasonerType.TEMPORAL],
            "after": [ReasonerType.TEMPORAL],
            "probably": [ReasonerType.PROBABILISTIC, ReasonerType.FUZZY],
            "maybe": [ReasonerType.PROBABILISTIC],
            "similar": [ReasonerType.ANALOGICAL, ReasonerType.CASEBASED],
            "like": [ReasonerType.ANALOGICAL],
            "prove": [ReasonerType.DEDUCTIVE],
            "logic": [ReasonerType.DEDUCTIVE],
            "pattern": [ReasonerType.INDUCTIVE],
            "diagnose": [ReasonerType.ABDUCTIVE],
            "know": [ReasonerType.EPISTEMIC],
            "believe": [ReasonerType.EPISTEMIC],
            "contradict": [ReasonerType.PARACONSISTENT],
            "approximately": [ReasonerType.FUZZY],
            "strategy": [ReasonerType.GAMETHEORY],
            "compete": [ReasonerType.GAMETHEORY],
            "negotiate": [ReasonerType.GAMETHEORY],
            "usually": [ReasonerType.DEFEASIBLE, ReasonerType.COMMONSENSE],
            "normally": [ReasonerType.DEFEASIBLE, ReasonerType.COMMONSENSE],
        }

        for pattern, reasoners in domain_patterns.items():
            if pattern in query_lower:
                for r in reasoners:
                    if r not in selected and r not in request.excluded_reasoners:
                        selected.append(r)

        # Default to deductive if nothing matches
        if not selected:
            selected = [ReasonerType.DEDUCTIVE, ReasonerType.COMMONSENSE]

        # Sort by success rate
        selected.sort(
            key=lambda r: self.registry.CAPABILITIES.get(r, ReasonerCapability(
                reasoner_type=r, strength_domains=[], weakness_domains=[],
                average_latency_ms=100, success_rate=0.5, confidence_calibration=0.5,
                complexity_threshold=0.5, requires_knowledge=False, supports_uncertainty=False
            )).success_rate,
            reverse=True
        )

        return selected[:5]  # Limit to top 5

    async def _execute_single(
        self,
        request: ReasoningRequest,
        reasoner: ReasonerType
    ) -> ReasoningResult:
        """Execute single reasoner."""
        step = await self._invoke_reasoner(reasoner, request.query, request.context)

        return ReasoningResult(
            success=step.confidence >= request.min_confidence,
            final_answer=step.output_data.get("answer"),
            confidence=step.confidence,
            chain=[step],
            reasoners_used=[reasoner],
            total_latency_ms=step.latency_ms,
            explanation=step.explanation
        )

    async def _execute_cascade(
        self,
        request: ReasoningRequest,
        reasoners: List[ReasonerType]
    ) -> ReasoningResult:
        """Execute reasoners in cascade until one succeeds."""
        chain = []

        for reasoner in reasoners:
            step = await self._invoke_reasoner(reasoner, request.query, request.context)
            chain.append(step)

            if step.confidence >= request.min_confidence:
                return ReasoningResult(
                    success=True,
                    final_answer=step.output_data.get("answer"),
                    confidence=step.confidence,
                    chain=chain,
                    reasoners_used=[s.reasoner for s in chain],
                    total_latency_ms=sum(s.latency_ms for s in chain),
                    explanation=step.explanation
                )

        # All failed - return best result
        best = max(chain, key=lambda s: s.confidence)
        return ReasoningResult(
            success=False,
            final_answer=best.output_data.get("answer"),
            confidence=best.confidence,
            chain=chain,
            reasoners_used=[s.reasoner for s in chain],
            total_latency_ms=sum(s.latency_ms for s in chain),
            explanation=f"No reasoner exceeded confidence threshold. Best: {best.reasoner.value}"
        )

    async def _execute_parallel(
        self,
        request: ReasoningRequest,
        reasoners: List[ReasonerType]
    ) -> ReasoningResult:
        """Execute reasoners in parallel and return best result."""
        tasks = [
            self._invoke_reasoner(r, request.query, request.context)
            for r in reasoners
        ]

        steps = await asyncio.gather(*tasks)
        chain = list(steps)

        # Select best result by confidence
        best = max(chain, key=lambda s: s.confidence)

        return ReasoningResult(
            success=best.confidence >= request.min_confidence,
            final_answer=best.output_data.get("answer"),
            confidence=best.confidence,
            chain=chain,
            reasoners_used=[s.reasoner for s in chain],
            total_latency_ms=max(s.latency_ms for s in chain),  # Parallel = max time
            explanation=f"Parallel execution. Best: {best.reasoner.value} ({best.confidence:.2f})"
        )

    async def _execute_ensemble(
        self,
        request: ReasoningRequest,
        reasoners: List[ReasonerType]
    ) -> ReasoningResult:
        """Execute reasoners and combine outputs via voting/aggregation."""
        tasks = [
            self._invoke_reasoner(r, request.query, request.context)
            for r in reasoners
        ]

        steps = await asyncio.gather(*tasks)
        chain = list(steps)

        # Weighted voting by confidence
        total_weight = sum(s.confidence for s in chain)
        if total_weight == 0:
            combined_confidence = 0
        else:
            combined_confidence = sum(s.confidence ** 2 for s in chain) / total_weight

        # Use highest confidence answer
        best = max(chain, key=lambda s: s.confidence)

        explanations = [f"{s.reasoner.value}: {s.explanation}" for s in chain]

        return ReasoningResult(
            success=combined_confidence >= request.min_confidence,
            final_answer=best.output_data.get("answer"),
            confidence=combined_confidence,
            chain=chain,
            reasoners_used=[s.reasoner for s in chain],
            total_latency_ms=max(s.latency_ms for s in chain),
            explanation="Ensemble: " + " | ".join(explanations)
        )

    async def _invoke_reasoner(
        self,
        reasoner: ReasonerType,
        query: str,
        context: Dict[str, Any]
    ) -> ReasoningStep:
        """Invoke a specific reasoning engine."""
        start_time = datetime.now()

        # Update metrics
        self._metrics[reasoner]["invocations"] += 1

        try:
            # In production, would actually call the reasoner module
            # For now, simulate based on capability profile
            cap = self.registry.get_capability(reasoner)

            # Simulate processing time
            await asyncio.sleep(cap.average_latency_ms / 1000 if cap else 0.1)

            # Generate result
            confidence = cap.success_rate if cap else 0.7

            output = {
                "answer": f"Reasoning result from {reasoner.value}",
                "reasoning_type": reasoner.value,
                "intermediate_steps": []
            }

            explanation = f"Applied {reasoner.value} reasoning to analyze the query"

            # Update success metrics
            self._metrics[reasoner]["successes"] += 1

            return ReasoningStep(
                reasoner=reasoner,
                input_data={"query": query, "context": context},
                output_data=output,
                confidence=confidence,
                latency_ms=self._elapsed_ms(start_time),
                explanation=explanation
            )

        except Exception as e:
            logger.error(f"Reasoner {reasoner.value} failed: {e}")
            return ReasoningStep(
                reasoner=reasoner,
                input_data={"query": query, "context": context},
                output_data={"error": str(e)},
                confidence=0,
                latency_ms=self._elapsed_ms(start_time),
                explanation=f"Error: {str(e)}"
            )

    def _elapsed_ms(self, start_time: datetime) -> float:
        """Calculate elapsed milliseconds."""
        return (datetime.now() - start_time).total_seconds() * 1000

    def get_metrics(self) -> Dict[str, Any]:
        """Get reasoning cascade metrics."""
        return {
            rtype.value: {
                **metrics,
                "success_rate": metrics["successes"] / metrics["invocations"] if metrics["invocations"] > 0 else 0
            }
            for rtype, metrics in self._metrics.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate Reasoning Cascade capabilities."""
    cascade = ReasoningCascade()
    await cascade.initialize()

    test_queries = [
        ("Why does smoking cause cancer?", ReasoningMode.CASCADE),
        ("What if Einstein had never been born?", ReasoningMode.SINGLE),
        ("Should AI be regulated?", ReasoningMode.ENSEMBLE),
        ("When did Rome fall and what happened after?", ReasoningMode.PARALLEL),
    ]

    for query, mode in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Mode: {mode.value}")

        request = ReasoningRequest(
            query=query,
            mode=mode,
            min_confidence=0.5
        )

        result = await cascade.reason(request)

        print(f"Success: {result.success}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoners: {[r.value for r in result.reasoners_used]}")
        print(f"Latency: {result.total_latency_ms:.1f}ms")
        print(f"Explanation: {result.explanation[:100]}...")


if __name__ == "__main__":
    asyncio.run(demo())
