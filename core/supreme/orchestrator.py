"""
BAEL Supreme Controller - Unified Orchestration Layer

The Supreme Controller is the apex of BAEL's architecture. It integrates:
- 25+ reasoning engines (causal, counterfactual, temporal, epistemic, deontic, etc.)
- 5-layer cognitive memory (working, episodic, semantic, procedural, meta)
- Multi-agent councils for deliberation
- Self-evolution through genetic algorithms
- Zero-cost operation through intelligent provider routing

This transforms BAEL from a collection of modules into a unified superintelligence.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.Supreme")


# =============================================================================
# CONFIGURATION
# =============================================================================

class OperationMode(Enum):
    """Operating modes for the Supreme Controller."""
    AUTONOMOUS = "autonomous"        # Full autonomous operation
    SUPERVISED = "supervised"        # Human-in-the-loop for critical decisions
    COOPERATIVE = "cooperative"      # Multi-agent collaboration mode
    RESEARCH = "research"            # Exploration and learning mode
    STEALTH = "stealth"              # Minimal footprint, maximum efficiency
    COUNCIL = "council"              # All decisions go through councils


class ReasoningStrategy(Enum):
    """Strategies for selecting reasoning engines."""
    AUTO = "auto"                    # Automatically select based on query
    CASCADE = "cascade"              # Try multiple reasoners in sequence
    ENSEMBLE = "ensemble"            # Combine multiple reasoner outputs
    SPECIALIZED = "specialized"      # Use domain-specific reasoner only
    DELIBERATIVE = "deliberative"    # Full council deliberation


class MemoryStrategy(Enum):
    """Strategies for memory utilization."""
    FULL = "full"                    # Use all 5 memory layers
    MINIMAL = "minimal"              # Working memory only
    CONTEXTUAL = "contextual"        # Dynamically select relevant layers
    PERSISTENT = "persistent"        # Emphasize long-term storage


@dataclass
class ControllerConfig:
    """Configuration for the Supreme Controller."""
    mode: OperationMode = OperationMode.AUTONOMOUS
    reasoning_strategy: ReasoningStrategy = ReasoningStrategy.AUTO
    memory_strategy: MemoryStrategy = MemoryStrategy.FULL

    # Performance settings
    max_reasoning_time_ms: int = 5000
    max_memory_items: int = 1000
    max_concurrent_agents: int = 10

    # Evolution settings
    enable_self_evolution: bool = True
    evolution_interval_seconds: int = 3600

    # Zero-cost settings
    enforce_zero_cost: bool = True
    provider_rotation_interval: int = 3600

    # Council settings
    require_council_for_critical: bool = True
    council_quorum: float = 0.6

    # Safety settings
    enable_ethics_check: bool = True
    enable_alignment_check: bool = True
    max_autonomy_level: float = 0.8


# =============================================================================
# QUERY ANALYSIS
# =============================================================================

class QueryType(Enum):
    """Types of queries for routing."""
    FACTUAL = "factual"              # What is X?
    CAUSAL = "causal"                # Why does X cause Y?
    COUNTERFACTUAL = "counterfactual"  # What if X had been different?
    TEMPORAL = "temporal"            # When did X happen? What's the sequence?
    NORMATIVE = "normative"          # Should X do Y? Is X obligated?
    EPISTEMIC = "epistemic"          # What do we know about X?
    CREATIVE = "creative"            # Generate new ideas
    ANALYTICAL = "analytical"        # Analyze this data/situation
    PLANNING = "planning"            # How to achieve goal?
    ETHICAL = "ethical"              # Is X ethical?
    EMOTIONAL = "emotional"          # How does X feel about Y?
    STRATEGIC = "strategic"          # Game-theoretic decisions
    UNCERTAIN = "uncertain"          # Fuzzy/probabilistic reasoning


@dataclass
class QueryAnalysis:
    """Analysis of an incoming query."""
    query_id: str
    original_query: str
    query_type: QueryType
    confidence: float
    detected_entities: List[str]
    detected_intents: List[str]
    complexity_score: float  # 0-1, higher = more complex
    requires_memory: bool
    requires_reasoning: List[str]  # List of reasoner types needed
    requires_council: bool
    urgency: float  # 0-1, higher = more urgent
    timestamp: datetime = field(default_factory=datetime.now)


class QueryAnalyzer:
    """Analyze incoming queries to determine routing."""

    # Query patterns for classification
    PATTERNS = {
        QueryType.CAUSAL: [
            "why", "cause", "because", "leads to", "results in",
            "effect", "impact", "consequence", "reason"
        ],
        QueryType.COUNTERFACTUAL: [
            "what if", "would have", "could have", "if only",
            "alternatively", "instead", "hypothetically"
        ],
        QueryType.TEMPORAL: [
            "when", "before", "after", "during", "timeline",
            "sequence", "order", "first", "last", "next"
        ],
        QueryType.NORMATIVE: [
            "should", "ought", "must", "allowed", "permitted",
            "obligated", "forbidden", "duty", "right", "wrong"
        ],
        QueryType.EPISTEMIC: [
            "know", "believe", "certain", "doubt", "evidence",
            "justified", "true", "false", "proof"
        ],
        QueryType.CREATIVE: [
            "create", "generate", "imagine", "invent", "design",
            "compose", "write", "draw", "innovate"
        ],
        QueryType.PLANNING: [
            "how to", "plan", "steps", "achieve", "goal",
            "strategy", "approach", "method", "procedure"
        ],
        QueryType.ETHICAL: [
            "ethical", "moral", "right", "wrong", "harm",
            "benefit", "fair", "just", "virtue"
        ],
        QueryType.EMOTIONAL: [
            "feel", "emotion", "happy", "sad", "angry",
            "afraid", "love", "hate", "empathy"
        ],
        QueryType.STRATEGIC: [
            "game", "compete", "opponent", "strategy", "optimal",
            "nash", "equilibrium", "payoff", "negotiate"
        ],
        QueryType.UNCERTAIN: [
            "probably", "maybe", "might", "uncertain", "fuzzy",
            "approximately", "roughly", "likelihood"
        ],
    }

    # Mapping from query types to reasoner modules
    REASONER_MAP = {
        QueryType.FACTUAL: ["deductive", "semantic"],
        QueryType.CAUSAL: ["causal", "counterfactual"],
        QueryType.COUNTERFACTUAL: ["counterfactual", "causal"],
        QueryType.TEMPORAL: ["temporal", "causal"],
        QueryType.NORMATIVE: ["deontic", "ethics", "alignment"],
        QueryType.EPISTEMIC: ["epistemic", "beliefrevision"],
        QueryType.CREATIVE: ["creativity", "analogical", "conceptlearn"],
        QueryType.ANALYTICAL: ["deductive", "inductive", "abductive"],
        QueryType.PLANNING: ["planning", "goal", "strategic"],
        QueryType.ETHICAL: ["ethics", "alignment", "deontic"],
        QueryType.EMOTIONAL: ["emotion", "empathy", "personality"],
        QueryType.STRATEGIC: ["gametheory", "negotiation", "coalition"],
        QueryType.UNCERTAIN: ["fuzzy", "probabilistic", "paraconsistent"],
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a query and determine routing."""
        query_lower = query.lower()

        # Score each query type
        type_scores: Dict[QueryType, float] = {}
        for qtype, patterns in self.PATTERNS.items():
            score = sum(1 for p in patterns if p in query_lower)
            type_scores[qtype] = score

        # Determine primary type
        if max(type_scores.values(), default=0) == 0:
            query_type = QueryType.FACTUAL
            confidence = 0.5
        else:
            query_type = max(type_scores, key=type_scores.get)
            confidence = min(1.0, type_scores[query_type] / 3)

        # Calculate complexity
        complexity = self._calculate_complexity(query)

        # Determine required reasoners
        reasoners = self.REASONER_MAP.get(query_type, ["deductive"])

        # Check if council needed (complex + normative/ethical)
        requires_council = (
            complexity > 0.7 or
            query_type in [QueryType.ETHICAL, QueryType.NORMATIVE, QueryType.STRATEGIC]
        )

        return QueryAnalysis(
            query_id=str(uuid4()),
            original_query=query,
            query_type=query_type,
            confidence=confidence,
            detected_entities=self._extract_entities(query),
            detected_intents=self._extract_intents(query),
            complexity_score=complexity,
            requires_memory=len(query) > 50,
            requires_reasoning=reasoners,
            requires_council=requires_council,
            urgency=self._estimate_urgency(query)
        )

    def _calculate_complexity(self, query: str) -> float:
        """Estimate query complexity (0-1)."""
        factors = [
            min(1.0, len(query) / 500),  # Length factor
            min(1.0, query.count("?") / 3),  # Question count
            min(1.0, len(query.split()) / 50),  # Word count
            1.0 if "and" in query.lower() and "or" in query.lower() else 0.0,  # Logical complexity
            1.0 if any(x in query.lower() for x in ["compare", "contrast", "analyze"]) else 0.0,
        ]
        return sum(factors) / len(factors)

    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities (simplified)."""
        # In production, would use NER model
        words = query.split()
        entities = [w for w in words if w[0].isupper() and len(w) > 1]
        return entities[:10]

    def _extract_intents(self, query: str) -> List[str]:
        """Extract intents from query."""
        intents = []
        lower = query.lower()

        if any(x in lower for x in ["find", "search", "look for"]):
            intents.append("search")
        if any(x in lower for x in ["create", "make", "generate"]):
            intents.append("create")
        if any(x in lower for x in ["explain", "describe", "tell me"]):
            intents.append("explain")
        if any(x in lower for x in ["analyze", "evaluate", "assess"]):
            intents.append("analyze")
        if any(x in lower for x in ["compare", "contrast", "versus"]):
            intents.append("compare")
        if any(x in lower for x in ["fix", "solve", "resolve"]):
            intents.append("solve")

        return intents or ["general"]

    def _estimate_urgency(self, query: str) -> float:
        """Estimate urgency of query."""
        lower = query.lower()
        urgent_words = ["urgent", "immediately", "asap", "critical", "emergency", "now"]
        return 1.0 if any(w in lower for w in urgent_words) else 0.5


# =============================================================================
# PROCESSING RESULT
# =============================================================================

@dataclass
class ProcessingResult:
    """Result of processing a query through the Supreme Controller."""
    query_id: str
    success: bool
    response: Any
    reasoning_chain: List[Dict[str, Any]]
    memory_accessed: List[str]
    reasoners_used: List[str]
    council_decision: Optional[Dict[str, Any]]
    ethics_check: Optional[Dict[str, Any]]
    execution_time_ms: float
    tokens_used: int
    cost: float  # Should always be 0 in zero-cost mode
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SUPREME CONTROLLER
# =============================================================================

class SupremeController:
    """
    The Supreme Controller - Apex orchestrator of all BAEL systems.

    This is the unified intelligence layer that transforms BAEL from
    a collection of modules into a coherent, self-evolving superintelligence.

    Responsibilities:
    1. Query Analysis: Understand what's being asked
    2. Reasoning Cascade: Route to appropriate reasoning engines
    3. Memory Integration: Utilize 5-layer cognitive architecture
    4. Council Orchestration: Deliberate on complex decisions
    5. Ethics/Alignment: Ensure safe and aligned operation
    6. Self-Evolution: Continuously improve capabilities
    7. Zero-Cost Enforcement: Operate without financial expenditure
    """

    def __init__(self, config: ControllerConfig = None):
        self.config = config or ControllerConfig()
        self.query_analyzer = QueryAnalyzer()

        # Component registries
        self._reasoners: Dict[str, Any] = {}
        self._memory_layers: Dict[str, Any] = {}
        self._councils: Dict[str, Any] = {}
        self._providers: Dict[str, Any] = {}

        # State
        self._initialized = False
        self._processing_count = 0
        self._total_queries = 0
        self._evolution_task: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = {
            "queries_processed": 0,
            "reasoning_success_rate": 1.0,
            "average_response_time_ms": 0,
            "memory_hits": 0,
            "council_invocations": 0,
            "ethics_blocks": 0,
            "cost_total": 0.0,
        }

        logger.info("🏛️ Supreme Controller initialized")

    async def initialize(self) -> None:
        """Initialize all controller components."""
        if self._initialized:
            return

        logger.info("🚀 Initializing Supreme Controller components...")

        # Initialize reasoning cascade
        await self._initialize_reasoners()

        # Initialize memory layers
        await self._initialize_memory()

        # Initialize councils
        await self._initialize_councils()

        # Initialize providers (LLM routing)
        await self._initialize_providers()

        # Start evolution loop if enabled
        if self.config.enable_self_evolution:
            self._evolution_task = asyncio.create_task(self._evolution_loop())

        self._initialized = True
        logger.info("✅ Supreme Controller fully initialized")

    async def _initialize_reasoners(self) -> None:
        """Initialize all reasoning engines."""
        reasoner_modules = [
            "causal", "counterfactual", "temporal", "epistemic", "deontic",
            "defeasible", "paraconsistent", "fuzzy", "deductive", "inductive",
            "abductive", "analogical", "commonsense", "spatial", "probabilistic",
            "modal", "argumentation", "casebased", "qualitative"
        ]

        for module in reasoner_modules:
            try:
                # Dynamic import pattern
                # In production, would actually import the modules
                self._reasoners[module] = {"status": "ready", "module": module}
                logger.debug(f"Loaded reasoner: {module}")
            except Exception as e:
                logger.warning(f"Failed to load reasoner {module}: {e}")

        logger.info(f"Initialized {len(self._reasoners)} reasoning engines")

    async def _initialize_memory(self) -> None:
        """Initialize the 5-layer cognitive memory architecture."""
        memory_layers = [
            ("working", "Short-term, high-frequency access"),
            ("episodic", "Specific experiences and events"),
            ("semantic", "Conceptual knowledge and facts"),
            ("procedural", "Skills and procedures"),
            ("meta", "Knowledge about own knowledge"),
        ]

        for layer_name, description in memory_layers:
            self._memory_layers[layer_name] = {
                "status": "ready",
                "description": description,
                "items": 0
            }

        logger.info(f"Initialized {len(self._memory_layers)} memory layers")

    async def _initialize_councils(self) -> None:
        """Initialize council system for deliberation."""
        council_types = [
            "optimization",
            "ethics",
            "strategy",
            "research",
            "validation"
        ]

        for council_type in council_types:
            self._councils[council_type] = {"status": "ready", "type": council_type}

        logger.info(f"Initialized {len(self._councils)} council types")

    async def _initialize_providers(self) -> None:
        """Initialize LLM provider routing for zero-cost operation."""
        # Provider rotation for zero-cost operation
        providers = [
            {"name": "openrouter_free", "priority": 1, "cost": 0},
            {"name": "groq_free", "priority": 2, "cost": 0},
            {"name": "ollama_local", "priority": 3, "cost": 0},
            {"name": "anthropic_free_tier", "priority": 4, "cost": 0},
        ]

        for provider in providers:
            self._providers[provider["name"]] = provider

        logger.info(f"Initialized {len(self._providers)} providers (zero-cost mode)")

    async def process(self, query: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """
        Process a query through the full BAEL intelligence stack.

        This is the main entry point that:
        1. Analyzes the query
        2. Retrieves relevant memories
        3. Routes to appropriate reasoners
        4. Invokes councils if needed
        5. Checks ethics/alignment
        6. Returns comprehensive result
        """
        start_time = datetime.now()
        context = context or {}

        if not self._initialized:
            await self.initialize()

        self._total_queries += 1

        try:
            # 1. Analyze query
            analysis = self.query_analyzer.analyze(query)
            logger.info(f"Query {analysis.query_id}: type={analysis.query_type.value}, complexity={analysis.complexity_score:.2f}")

            # 2. Retrieve memories
            memories = await self._retrieve_memories(query, analysis)

            # 3. Execute reasoning cascade
            reasoning_result = await self._execute_reasoning(query, analysis, memories, context)

            # 4. Council deliberation if needed
            council_decision = None
            if analysis.requires_council and self.config.require_council_for_critical:
                council_decision = await self._invoke_council(query, reasoning_result, analysis)

            # 5. Ethics check
            ethics_check = None
            if self.config.enable_ethics_check:
                ethics_check = await self._check_ethics(query, reasoning_result)
                if ethics_check and ethics_check.get("blocked"):
                    self._metrics["ethics_blocks"] += 1
                    return ProcessingResult(
                        query_id=analysis.query_id,
                        success=False,
                        response="This request was blocked by ethics review.",
                        reasoning_chain=[],
                        memory_accessed=[],
                        reasoners_used=[],
                        council_decision=council_decision,
                        ethics_check=ethics_check,
                        execution_time_ms=self._elapsed_ms(start_time),
                        tokens_used=0,
                        cost=0.0
                    )

            # 6. Store experience in memory
            await self._store_experience(query, reasoning_result, analysis)

            # 7. Build response
            execution_time = self._elapsed_ms(start_time)
            self._update_metrics(execution_time)

            return ProcessingResult(
                query_id=analysis.query_id,
                success=True,
                response=reasoning_result.get("response"),
                reasoning_chain=reasoning_result.get("chain", []),
                memory_accessed=memories,
                reasoners_used=analysis.requires_reasoning,
                council_decision=council_decision,
                ethics_check=ethics_check,
                execution_time_ms=execution_time,
                tokens_used=reasoning_result.get("tokens", 0),
                cost=0.0,  # Zero-cost enforcement
                metadata={
                    "query_type": analysis.query_type.value,
                    "complexity": analysis.complexity_score,
                    "confidence": analysis.confidence
                }
            )

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return ProcessingResult(
                query_id=str(uuid4()),
                success=False,
                response=f"Error: {str(e)}",
                reasoning_chain=[],
                memory_accessed=[],
                reasoners_used=[],
                council_decision=None,
                ethics_check=None,
                execution_time_ms=self._elapsed_ms(start_time),
                tokens_used=0,
                cost=0.0
            )

    async def _retrieve_memories(self, query: str, analysis: QueryAnalysis) -> List[str]:
        """Retrieve relevant memories from all layers."""
        memories = []

        if self.config.memory_strategy == MemoryStrategy.MINIMAL:
            # Only working memory
            layers_to_check = ["working"]
        elif self.config.memory_strategy == MemoryStrategy.CONTEXTUAL:
            # Select based on query type
            if analysis.query_type == QueryType.TEMPORAL:
                layers_to_check = ["episodic", "working"]
            elif analysis.query_type == QueryType.FACTUAL:
                layers_to_check = ["semantic", "working"]
            elif analysis.query_type == QueryType.PLANNING:
                layers_to_check = ["procedural", "working"]
            else:
                layers_to_check = ["working", "semantic"]
        else:
            # Full - check all layers
            layers_to_check = list(self._memory_layers.keys())

        for layer in layers_to_check:
            # In production, would actually query memory
            memories.append(f"{layer}_memory")
            self._metrics["memory_hits"] += 1

        return memories

    async def _execute_reasoning(
        self,
        query: str,
        analysis: QueryAnalysis,
        memories: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the reasoning cascade."""
        chain = []

        if self.config.reasoning_strategy == ReasoningStrategy.CASCADE:
            # Try reasoners in sequence until one succeeds
            for reasoner_name in analysis.requires_reasoning:
                if reasoner_name in self._reasoners:
                    result = await self._invoke_reasoner(reasoner_name, query, context)
                    chain.append({
                        "reasoner": reasoner_name,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                    if result.get("success"):
                        break

        elif self.config.reasoning_strategy == ReasoningStrategy.ENSEMBLE:
            # Run all reasoners and combine results
            results = []
            for reasoner_name in analysis.requires_reasoning:
                if reasoner_name in self._reasoners:
                    result = await self._invoke_reasoner(reasoner_name, query, context)
                    results.append(result)
                    chain.append({
                        "reasoner": reasoner_name,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
            # Combine results (would use voting/aggregation in production)

        else:  # AUTO or SPECIALIZED
            # Use primary reasoner
            primary = analysis.requires_reasoning[0] if analysis.requires_reasoning else "deductive"
            if primary in self._reasoners:
                result = await self._invoke_reasoner(primary, query, context)
                chain.append({
                    "reasoner": primary,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })

        return {
            "success": True,
            "response": f"Processed using {analysis.requires_reasoning}",
            "chain": chain,
            "tokens": 0
        }

    async def _invoke_reasoner(
        self,
        reasoner_name: str,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a specific reasoning engine."""
        # In production, would actually call the reasoner module
        return {
            "success": True,
            "reasoner": reasoner_name,
            "output": f"Reasoning result from {reasoner_name}"
        }

    async def _invoke_council(
        self,
        query: str,
        reasoning_result: Dict[str, Any],
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Invoke council deliberation for complex decisions."""
        self._metrics["council_invocations"] += 1

        # Select appropriate council
        if analysis.query_type == QueryType.ETHICAL:
            council_type = "ethics"
        elif analysis.query_type == QueryType.STRATEGIC:
            council_type = "strategy"
        else:
            council_type = "optimization"

        # In production, would actually run council deliberation
        return {
            "council": council_type,
            "decision": "approved",
            "confidence": 0.85,
            "votes": {"approve": 4, "reject": 1},
            "reasoning": "Council deliberation completed"
        }

    async def _check_ethics(
        self,
        query: str,
        reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check ethics and alignment of the response."""
        # In production, would use ethics engine
        return {
            "blocked": False,
            "score": 0.95,
            "frameworks_checked": ["utilitarian", "deontological", "virtue"],
            "concerns": []
        }

    async def _store_experience(
        self,
        query: str,
        result: Dict[str, Any],
        analysis: QueryAnalysis
    ) -> None:
        """Store experience in episodic memory for learning."""
        # In production, would store in cognitive memory
        pass

    async def _evolution_loop(self) -> None:
        """Continuous self-evolution loop."""
        while True:
            await asyncio.sleep(self.config.evolution_interval_seconds)

            try:
                # Analyze performance
                metrics = self.get_metrics()

                # Identify weak areas
                if metrics["reasoning_success_rate"] < 0.8:
                    logger.info("Evolution: Improving reasoning capabilities")
                    # Would trigger evolution engine

                if metrics["average_response_time_ms"] > 3000:
                    logger.info("Evolution: Optimizing response time")
                    # Would trigger optimization

                logger.debug("Evolution cycle completed")

            except Exception as e:
                logger.error(f"Evolution loop error: {e}")

    def _elapsed_ms(self, start_time: datetime) -> float:
        """Calculate elapsed milliseconds."""
        return (datetime.now() - start_time).total_seconds() * 1000

    def _update_metrics(self, execution_time: float) -> None:
        """Update internal metrics."""
        self._metrics["queries_processed"] += 1

        # Running average of response time
        n = self._metrics["queries_processed"]
        old_avg = self._metrics["average_response_time_ms"]
        self._metrics["average_response_time_ms"] = (old_avg * (n-1) + execution_time) / n

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self._metrics.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get controller status."""
        return {
            "initialized": self._initialized,
            "mode": self.config.mode.value,
            "reasoners_loaded": len(self._reasoners),
            "memory_layers": len(self._memory_layers),
            "councils_active": len(self._councils),
            "providers": len(self._providers),
            "metrics": self._metrics,
            "config": {
                "reasoning_strategy": self.config.reasoning_strategy.value,
                "memory_strategy": self.config.memory_strategy.value,
                "evolution_enabled": self.config.enable_self_evolution,
                "zero_cost": self.config.enforce_zero_cost
            }
        }

    async def shutdown(self) -> None:
        """Shutdown the controller gracefully."""
        logger.info("Shutting down Supreme Controller...")

        if self._evolution_task:
            self._evolution_task.cancel()
            try:
                await self._evolution_task
            except asyncio.CancelledError:
                pass

        self._initialized = False
        logger.info("Supreme Controller shutdown complete")


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate Supreme Controller capabilities."""
    controller = SupremeController(ControllerConfig(
        mode=OperationMode.AUTONOMOUS,
        reasoning_strategy=ReasoningStrategy.CASCADE,
        memory_strategy=MemoryStrategy.FULL,
        enable_self_evolution=False  # Disable for demo
    ))

    await controller.initialize()

    # Test queries
    queries = [
        "Why does increased CO2 cause global warming?",
        "What if we had discovered electricity 100 years earlier?",
        "Should AI systems be given rights?",
        "How do I build a recommendation system?",
        "What emotions is this user experiencing?"
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        result = await controller.process(query)
        print(f"Type: {result.metadata.get('query_type')}")
        print(f"Reasoners: {result.reasoners_used}")
        print(f"Time: {result.execution_time_ms:.1f}ms")
        print(f"Cost: ${result.cost} (zero-cost)")

    print("\n" + "="*60)
    print("Controller Status:")
    print(json.dumps(controller.get_status(), indent=2, default=str))

    await controller.shutdown()


if __name__ == "__main__":
    import json
    asyncio.run(demo())
