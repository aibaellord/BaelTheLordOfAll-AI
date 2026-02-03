"""
BAEL Singularity Integration Engine
====================================

This module integrates ALL dormant capabilities into active workflows.
It's the "neural network" that connects every capability to every other.

Key Integrations:
- Creativity + Decision Making = Creative Solutions
- Curiosity + Research = Autonomous Exploration
- Emotion + Reasoning = Human-like Judgment
- Intuition + Analysis = Fast-then-Slow Thinking
- Game Theory + Negotiation = Strategic Interaction
- Trust + Coalition = Dynamic Team Formation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Singularity.Integration")


# =============================================================================
# INTEGRATION PATTERNS
# =============================================================================

class IntegrationPattern(Enum):
    """Patterns for capability integration."""
    SEQUENTIAL = "sequential"      # A → B → C
    PARALLEL = "parallel"          # A, B, C → Merge
    CASCADING = "cascading"        # A triggers B if condition
    FEEDBACK = "feedback"          # A → B → A (loop)
    CONSENSUS = "consensus"        # All must agree
    COMPETITIVE = "competitive"    # Best result wins
    WEIGHTED = "weighted"          # Weighted combination
    ADAPTIVE = "adaptive"          # Changes based on context


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    name: str
    pattern: IntegrationPattern
    capabilities: List[str]
    weights: Optional[Dict[str, float]] = None
    conditions: Optional[Dict[str, Callable]] = None
    fallback: Optional[str] = None


@dataclass
class IntegrationResult:
    """Result of an integration."""
    success: bool
    data: Any
    capabilities_used: List[str]
    pattern: IntegrationPattern
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CORE INTEGRATIONS
# =============================================================================

class SingularityIntegrations:
    """
    Pre-defined integrations that connect BAEL's capabilities.
    """

    # Creativity + Decision = Creative Solutions
    CREATIVE_SOLUTIONS = IntegrationConfig(
        name="creative_solutions",
        pattern=IntegrationPattern.SEQUENTIAL,
        capabilities=["creativity", "reasoning", "decision"],
        weights={"creativity": 0.5, "reasoning": 0.3, "decision": 0.2}
    )

    # Curiosity + Research = Autonomous Exploration
    AUTONOMOUS_EXPLORATION = IntegrationConfig(
        name="autonomous_exploration",
        pattern=IntegrationPattern.FEEDBACK,
        capabilities=["curiosity", "research", "memory", "learning"]
    )

    # Emotion + Reasoning = Human-like Judgment
    HUMANLIKE_JUDGMENT = IntegrationConfig(
        name="humanlike_judgment",
        pattern=IntegrationPattern.WEIGHTED,
        capabilities=["emotion", "intuition", "reasoning", "ethics"],
        weights={"emotion": 0.2, "intuition": 0.3, "reasoning": 0.4, "ethics": 0.1}
    )

    # Intuition + Analysis = Fast-then-Slow
    FAST_THEN_SLOW = IntegrationConfig(
        name="fast_then_slow",
        pattern=IntegrationPattern.CASCADING,
        capabilities=["intuition", "extended_thinking", "metacognition"],
        conditions={"extended_thinking": lambda r: r.get("confidence", 1.0) < 0.8}
    )

    # Game Theory + Negotiation = Strategic Interaction
    STRATEGIC_INTERACTION = IntegrationConfig(
        name="strategic_interaction",
        pattern=IntegrationPattern.SEQUENTIAL,
        capabilities=["game_theory", "negotiation", "trust"]
    )

    # Trust + Coalition = Dynamic Teams
    DYNAMIC_TEAMS = IntegrationConfig(
        name="dynamic_teams",
        pattern=IntegrationPattern.PARALLEL,
        capabilities=["trust", "reputation", "coalition_manager", "swarm_intelligence"]
    )

    # Multi-Modal Reasoning
    MULTI_MODAL_REASONING = IntegrationConfig(
        name="multi_modal_reasoning",
        pattern=IntegrationPattern.CONSENSUS,
        capabilities=[
            "causal_reasoning", "counterfactual", "probabilistic",
            "deductive", "inductive", "analogical"
        ]
    )

    # Creative Problem Solving
    CREATIVE_PROBLEM_SOLVING = IntegrationConfig(
        name="creative_problem_solving",
        pattern=IntegrationPattern.ADAPTIVE,
        capabilities=[
            "creativity", "curiosity", "constraint_solver",
            "heuristic", "evolution", "swarm_intelligence"
        ]
    )

    # Autonomous Learning
    AUTONOMOUS_LEARNING = IntegrationConfig(
        name="autonomous_learning",
        pattern=IntegrationPattern.FEEDBACK,
        capabilities=[
            "curiosity", "meta_learning", "reinforcement",
            "active_learning", "feedback_learning"
        ]
    )

    # Total Awareness
    TOTAL_AWARENESS = IntegrationConfig(
        name="total_awareness",
        pattern=IntegrationPattern.PARALLEL,
        capabilities=[
            "vision", "voice", "computer_use",
            "proactive", "attention", "memory_manager"
        ]
    )


# =============================================================================
# INTEGRATION ENGINE
# =============================================================================

class IntegrationEngine:
    """
    Engine that executes capability integrations.
    """

    def __init__(self, singularity):
        self.singularity = singularity
        self._integrations: Dict[str, IntegrationConfig] = {}
        self._load_default_integrations()

    def _load_default_integrations(self):
        """Load default integrations."""
        for attr_name in dir(SingularityIntegrations):
            if not attr_name.startswith('_'):
                config = getattr(SingularityIntegrations, attr_name)
                if isinstance(config, IntegrationConfig):
                    self._integrations[config.name] = config

    async def execute(
        self,
        integration_name: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute an integration.

        Args:
            integration_name: Name of the integration
            input_data: Input to process
            context: Optional context

        Returns:
            IntegrationResult with combined output
        """
        if integration_name not in self._integrations:
            raise ValueError(f"Unknown integration: {integration_name}")

        config = self._integrations[integration_name]
        start_time = datetime.now()

        try:
            if config.pattern == IntegrationPattern.SEQUENTIAL:
                result = await self._execute_sequential(config, input_data, context)
            elif config.pattern == IntegrationPattern.PARALLEL:
                result = await self._execute_parallel(config, input_data, context)
            elif config.pattern == IntegrationPattern.CASCADING:
                result = await self._execute_cascading(config, input_data, context)
            elif config.pattern == IntegrationPattern.FEEDBACK:
                result = await self._execute_feedback(config, input_data, context)
            elif config.pattern == IntegrationPattern.CONSENSUS:
                result = await self._execute_consensus(config, input_data, context)
            elif config.pattern == IntegrationPattern.COMPETITIVE:
                result = await self._execute_competitive(config, input_data, context)
            elif config.pattern == IntegrationPattern.WEIGHTED:
                result = await self._execute_weighted(config, input_data, context)
            elif config.pattern == IntegrationPattern.ADAPTIVE:
                result = await self._execute_adaptive(config, input_data, context)
            else:
                result = await self._execute_sequential(config, input_data, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            return IntegrationResult(
                success=True,
                data=result,
                capabilities_used=config.capabilities,
                pattern=config.pattern,
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"Integration {integration_name} failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()

            return IntegrationResult(
                success=False,
                data={"error": str(e)},
                capabilities_used=config.capabilities,
                pattern=config.pattern,
                execution_time=execution_time
            )

    async def _execute_sequential(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute capabilities in sequence, piping output to next."""
        current_data = input_data

        for capability in config.capabilities:
            try:
                result = await self.singularity.invoke(
                    capability,
                    "process",
                    input=current_data,
                    context=context
                )
                current_data = result
            except Exception as e:
                logger.warning(f"Sequential step {capability} failed: {e}")
                if config.fallback:
                    return await self.singularity.invoke(
                        config.fallback, "process", input=input_data
                    )
                raise

        return current_data

    async def _execute_parallel(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute capabilities in parallel and merge results."""
        tasks = []

        for capability in config.capabilities:
            task = self.singularity.invoke(
                capability,
                "process",
                input=input_data,
                context=context
            )
            tasks.append((capability, task))

        results = {}
        for capability, task in tasks:
            try:
                results[capability] = await task
            except Exception as e:
                logger.warning(f"Parallel task {capability} failed: {e}")
                results[capability] = {"error": str(e)}

        return self._merge_results(results, config.weights)

    async def _execute_cascading(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute capabilities conditionally."""
        current_data = input_data

        for capability in config.capabilities:
            # Check condition if exists
            if config.conditions and capability in config.conditions:
                condition = config.conditions[capability]
                if not condition(current_data):
                    continue

            try:
                result = await self.singularity.invoke(
                    capability,
                    "process",
                    input=current_data,
                    context=context
                )
                current_data = result
            except Exception as e:
                logger.warning(f"Cascading step {capability} failed: {e}")

        return current_data

    async def _execute_feedback(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict],
        max_iterations: int = 5
    ) -> Any:
        """Execute with feedback loop."""
        current_data = input_data
        iterations = 0

        while iterations < max_iterations:
            for capability in config.capabilities:
                try:
                    result = await self.singularity.invoke(
                        capability,
                        "process",
                        input=current_data,
                        context=context,
                        iteration=iterations
                    )
                    current_data = result
                except Exception as e:
                    logger.warning(f"Feedback step {capability} failed: {e}")

            # Check convergence
            if self._check_convergence(current_data, input_data):
                break

            iterations += 1

        return current_data

    async def _execute_consensus(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute and require consensus."""
        results = await self._execute_parallel(config, input_data, context)

        # Check for consensus
        if isinstance(results, dict):
            values = [v for v in results.values() if not isinstance(v, dict) or "error" not in v]
            if len(values) > 0:
                # Simple consensus: majority vote or average
                return self._find_consensus(values)

        return results

    async def _execute_competitive(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute and select best result."""
        results = await self._execute_parallel(config, input_data, context)

        # Score results and select best
        best_score = -float('inf')
        best_result = None

        for capability, result in results.items():
            if isinstance(result, dict) and "error" in result:
                continue

            score = self._score_result(result, config.weights.get(capability, 1.0) if config.weights else 1.0)
            if score > best_score:
                best_score = score
                best_result = result

        return best_result or results

    async def _execute_weighted(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Execute with weighted combination."""
        results = await self._execute_parallel(config, input_data, context)
        return self._merge_results(results, config.weights)

    async def _execute_adaptive(
        self,
        config: IntegrationConfig,
        input_data: Any,
        context: Optional[Dict]
    ) -> Any:
        """Adaptive execution based on context."""
        # Analyze context to determine best pattern
        context_type = self._analyze_context(input_data, context)

        if context_type == "simple":
            return await self._execute_sequential(config, input_data, context)
        elif context_type == "complex":
            return await self._execute_parallel(config, input_data, context)
        elif context_type == "iterative":
            return await self._execute_feedback(config, input_data, context)
        else:
            return await self._execute_weighted(config, input_data, context)

    def _merge_results(
        self,
        results: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Merge results from multiple capabilities."""
        merged = {
            "combined": True,
            "sources": list(results.keys()),
            "outputs": {}
        }

        for capability, result in results.items():
            weight = weights.get(capability, 1.0) if weights else 1.0
            merged["outputs"][capability] = {
                "result": result,
                "weight": weight
            }

        return merged

    def _check_convergence(self, current: Any, previous: Any) -> bool:
        """Check if feedback loop has converged."""
        # Simple check - in practice would be more sophisticated
        if isinstance(current, dict) and isinstance(previous, dict):
            return current == previous
        return False

    def _find_consensus(self, values: List[Any]) -> Any:
        """Find consensus among values."""
        # Simple: return first value
        # In practice: voting, averaging, etc.
        return values[0] if values else None

    def _score_result(self, result: Any, weight: float) -> float:
        """Score a result for competition."""
        base_score = 1.0

        if isinstance(result, dict):
            if "confidence" in result:
                base_score = result["confidence"]
            elif "score" in result:
                base_score = result["score"]

        return base_score * weight

    def _analyze_context(self, input_data: Any, context: Optional[Dict]) -> str:
        """Analyze context to determine execution pattern."""
        if context and context.get("iterative"):
            return "iterative"

        if isinstance(input_data, str):
            if len(input_data) > 1000:
                return "complex"
            return "simple"

        return "weighted"

    def list_integrations(self) -> List[str]:
        """List available integrations."""
        return list(self._integrations.keys())

    def get_integration(self, name: str) -> Optional[IntegrationConfig]:
        """Get integration config."""
        return self._integrations.get(name)

    def register_integration(self, config: IntegrationConfig):
        """Register a custom integration."""
        self._integrations[config.name] = config


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

class WorkflowBuilder:
    """
    Build complex workflows from integrations.
    """

    def __init__(self, integration_engine: IntegrationEngine):
        self.engine = integration_engine
        self._steps: List[Tuple[str, Dict[str, Any]]] = []

    def add(self, integration_name: str, **kwargs) -> "WorkflowBuilder":
        """Add an integration step."""
        self._steps.append((integration_name, kwargs))
        return self

    def chain(self, *integration_names: str) -> "WorkflowBuilder":
        """Chain multiple integrations."""
        for name in integration_names:
            self._steps.append((name, {}))
        return self

    async def execute(
        self,
        input_data: Any,
        context: Optional[Dict] = None
    ) -> List[IntegrationResult]:
        """Execute the workflow."""
        results = []
        current_data = input_data

        for integration_name, kwargs in self._steps:
            result = await self.engine.execute(
                integration_name,
                current_data,
                {**(context or {}), **kwargs}
            )
            results.append(result)

            if result.success:
                current_data = result.data
            else:
                break

        return results

    def reset(self) -> "WorkflowBuilder":
        """Reset the workflow."""
        self._steps = []
        return self


# =============================================================================
# FACTORY
# =============================================================================

def create_integration_engine(singularity) -> IntegrationEngine:
    """Create an integration engine."""
    return IntegrationEngine(singularity)


def create_workflow_builder(singularity) -> WorkflowBuilder:
    """Create a workflow builder."""
    engine = create_integration_engine(singularity)
    return WorkflowBuilder(engine)
