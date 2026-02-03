"""
Phase 2 Orchestration Hub for BAEL

Central orchestrator that integrates all Phase 2 systems:
- Advanced Reasoning
- Adaptive Learning
- Agent Swarms
- Tool Composition
- Predictive Planning
- Knowledge Graph
- Cost Optimization
- Self-Diagnostics

Creates unified, intelligent system with continuous improvement and self-optimization.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .composition import (CompositionEngine, ToolDefinition, Workflow,
                          get_composition_engine)
from .cost_optimizer import (APIProvider, APITier, CostOptimizer, ResourceType,
                             get_cost_optimizer)
from .diagnostics import (ComponentType, DiagnosticsSystem, PerformanceProfile,
                          get_diagnostics_system)
from .knowledge_graph import (Entity, EntityType, KnowledgeGraphEngine,
                              Relationship, get_knowledge_graph_engine)
from .learning import (AdaptiveLearner, LearningDomain, Outcome, OutcomeType,
                       get_adaptive_learner)
from .planning import Plan, PlanningEngine, get_planning_engine
# Import all Phase 2 modules
from .reasoning import (ReasoningEngine, ReasoningPremise, ReasoningType,
                        get_reasoning_engine)
from .swarms import Swarm, SwarmOrchestrator, Task, get_swarm_orchestrator

logger = logging.getLogger(__name__)


class AgentMode(str, Enum):
    """Operating mode for the system."""
    CONSERVATIVE = "conservative"  # Focus on reliability
    BALANCED = "balanced"  # Good balance of speed and reliability
    AGGRESSIVE = "aggressive"  # Optimize for speed
    LEARNING = "learning"  # Maximize learning and improvement
    AUTONOMOUS = "autonomous"  # Fully autonomous optimization


@dataclass
class TaskRequest:
    """Request for task execution."""
    task_id: str
    description: str
    goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    mode: AgentMode = AgentMode.BALANCED
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "goal": self.goal,
            "context": self.context,
            "constraints": self.constraints,
            "required_capabilities": self.required_capabilities,
            "mode": self.mode.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionResult:
    """Result of task execution."""
    task_id: str
    success: bool
    output: Any
    reasoning_trace: Optional[str] = None
    plan_used: Optional[str] = None
    swarm_id: Optional[str] = None
    composition_id: Optional[str] = None
    confidence: float = 0.0
    execution_time_ms: float = 0.0
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "reasoning_trace": self.reasoning_trace,
            "plan_used": self.plan_used,
            "swarm_id": self.swarm_id,
            "composition_id": self.composition_id,
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms,
            "cost": self.cost,
            "metadata": self.metadata,
        }


class Phase2Orchestrator:
    """Main orchestrator for all Phase 2 systems."""

    def __init__(self):
        """Initialize Phase 2 orchestrator."""
        # Initialize all systems
        self.reasoning_engine = get_reasoning_engine()
        self.adaptive_learner = get_adaptive_learner()
        self.swarm_orchestrator = get_swarm_orchestrator()
        self.composition_engine = get_composition_engine()
        self.planning_engine = get_planning_engine()
        self.knowledge_graph = get_knowledge_graph_engine()
        self.cost_optimizer = get_cost_optimizer(monthly_budget=0.0)  # Free-only strategy
        self.diagnostics = get_diagnostics_system()

        # Execution tracking
        self.execution_history: Dict[str, ExecutionResult] = {}
        self.current_mode = AgentMode.BALANCED
        self.system_initialized_at = datetime.now()

        # Callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            "task_started": [],
            "task_completed": [],
            "task_failed": [],
            "optimization_triggered": [],
            "learning_event": [],
        }

        logger.info("Phase 2 Orchestrator initialized successfully")

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callback for event."""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, data: Any) -> None:
        """Trigger callbacks for event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def set_mode(self, mode: AgentMode) -> None:
        """Set operating mode."""
        self.current_mode = mode
        logger.info(f"Mode changed to: {mode.value}")

    def execute_task(
        self,
        task_request: TaskRequest,
    ) -> ExecutionResult:
        """
        Execute task using Phase 2 systems.

        Orchestrates:
        1. Planning (predictive planning + scenario analysis)
        2. Knowledge (extract from request and KB)
        3. Reasoning (multi-step logical reasoning)
        4. Composition (create tool workflow)
        5. Execution (swarms + composition)
        6. Learning (learn from outcome)
        7. Optimization (cost + performance)
        """
        start_time = datetime.now()
        self._trigger_callbacks("task_started", task_request)

        try:
            # Step 1: Planning
            logger.info(f"Planning task: {task_request.goal}")
            plan = self.planning_engine.create_plan(
                task_request.goal,
                task_request.context,
                task_request.constraints,
            )

            # Step 2: Knowledge extraction and reasoning
            logger.info("Extracting knowledge and reasoning")
            knowledge_learned = self.knowledge_graph.learn_from_text(
                task_request.description
            )

            premises = [
                ReasoningPremise(
                    statement=task_request.goal,
                    type="goal",
                    confidence=0.9,
                    source="task_request",
                )
            ]

            reasoning_trace = self.reasoning_engine.reason(
                query=task_request.goal,
                premises=premises,
                reasoning_type=ReasoningType.ABDUCTIVE,
                constraints=task_request.constraints,
            )

            # Step 3: Tool composition
            logger.info("Composing tool workflow")
            workflow = self.composition_engine.compose(
                goal=task_request.goal,
                required_capabilities=task_request.required_capabilities,
                constraints=task_request.constraints,
            )

            # Step 4: Cost optimization
            logger.info("Optimizing for cost")
            optimization = self.cost_optimizer.optimize_request(
                ResourceType.API_CALL,
                task_request.context,
            )

            # Step 5: Execute with swarms if task is complex
            output = None
            swarm_id = None

            if len(task_request.required_capabilities) > 1:
                logger.info("Creating swarm for complex task")
                swarm = self.swarm_orchestrator.create_swarm(num_agents=4)
                swarm_id = swarm.swarm_id

                # Create task
                main_task = Task(
                    task_id=task_request.task_id,
                    description=task_request.description,
                    priority=8,
                )
                swarm.submit_task(main_task, decompose=True)
                output = swarm.get_swarm_status()

            # Step 6: Record learning
            outcome = Outcome(
                action_id=task_request.task_id,
                action_description=task_request.description,
                outcome_type=OutcomeType.SUCCESS if output else OutcomeType.FAILURE,
                success_score=0.8 if output else 0.2,
                execution_time=(datetime.now() - start_time).total_seconds() * 1000,
                resource_usage={"compute": 0.5, "memory": 0.3},
                domain=LearningDomain.STRATEGY_ADAPTATION,
            )
            self.adaptive_learner.record_outcome(outcome)

            # Step 7: Create execution result
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result = ExecutionResult(
                task_id=task_request.task_id,
                success=output is not None,
                output=output or {"status": "execution_details"},
                reasoning_trace=self.reasoning_engine.explain_conclusion(
                    reasoning_trace.trace_id
                ),
                plan_used=plan.plan_id,
                swarm_id=swarm_id,
                composition_id=workflow.workflow_id if workflow else None,
                confidence=reasoning_trace.final_confidence,
                execution_time_ms=execution_time,
                cost=optimization.get("cost", 0.0),
                metadata={
                    "knowledge_learned": knowledge_learned,
                    "plan_quality": plan.quality.value,
                    "reasoning_quality": reasoning_trace.reasoning_quality,
                    "optimization": optimization,
                    "adaptive_learner_stats": self.adaptive_learner.export_learning_profile(),
                },
            )

            self.execution_history[task_request.task_id] = result
            self._trigger_callbacks("task_completed", result)
            logger.info(f"Task completed: {task_request.task_id}")

            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            error_result = ExecutionResult(
                task_id=task_request.task_id,
                success=False,
                output={"error": str(e)},
                confidence=0.0,
                execution_time_ms=(
                    datetime.now() - start_time
                ).total_seconds() * 1000,
            )
            self.execution_history[task_request.task_id] = error_result
            self._trigger_callbacks("task_failed", error_result)
            return error_result

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics."""
        diagnostics = self.diagnostics.run_diagnostics()

        # Add Phase 2 specific info
        diagnostics["phase2"] = {
            "reasoning_engine": "initialized",
            "adaptive_learner": {
                "success_rate": self.adaptive_learner.get_success_rate(),
                "num_strategies": len(self.adaptive_learner.strategies),
            },
            "swarms": {
                "num_active": len(self.swarm_orchestrator.swarms),
            },
            "knowledge_graph": self.knowledge_graph.get_statistics(),
            "cost_optimization": self.cost_optimizer.get_optimization_report(),
            "mode": self.current_mode.value,
        }

        return diagnostics

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (
                datetime.now() - self.system_initialized_at
            ).total_seconds(),
            "mode": self.current_mode.value,
            "tasks_executed": len(self.execution_history),
            "success_rate": self._calculate_success_rate(),
            "diagnostics": self.run_diagnostics(),
            "learning_profile": self.adaptive_learner.export_learning_profile(),
        }

    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        if not self.execution_history:
            return 0.0

        successes = sum(
            1 for r in self.execution_history.values() if r.success
        )
        return successes / len(self.execution_history)

    def optimize_system(self) -> List[str]:
        """Optimize system based on metrics."""
        actions = []

        # Get performance profile
        if self.execution_history:
            latencies = [
                r.execution_time_ms
                for r in self.execution_history.values()
                if r.success
            ]

            if latencies:
                avg_latency = sum(latencies) / len(latencies)

                profile = PerformanceProfile(
                    avg_latency_ms=avg_latency,
                    error_rate=1.0 - self._calculate_success_rate(),
                    cpu_usage=0.5,
                    memory_usage=0.4,
                    cache_hit_rate=0.75,
                )

                self.diagnostics.record_performance(profile)
                actions = self.diagnostics.optimization_trigger.evaluate(profile)

        return actions

    def export_knowledge_base(self) -> Dict[str, Any]:
        """Export knowledge base snapshot."""
        return {
            "timestamp": datetime.now().isoformat(),
            "knowledge_graph": self.knowledge_graph.graph.to_dict(),
            "learning_profile": self.adaptive_learner.export_learning_profile(),
            "execution_history": {
                tid: r.to_dict()
                for tid, r in self.execution_history.items()
            },
            "plans_created": len(self.planning_engine.plans),
            "workflows_created": len(self.composition_engine.workflows),
        }


# Global Phase 2 orchestrator
_orchestrator = None


def get_phase2_orchestrator() -> Phase2Orchestrator:
    """Get or create global Phase 2 orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Phase2Orchestrator()
    return _orchestrator
