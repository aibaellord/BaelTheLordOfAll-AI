"""
BAEL - Micro-Agent Swarm Force Multiplier
==========================================

Force multiply genius output through micro-agent coordination.

Features:
1. Agent Spawning - Create specialized micro-agents on demand
2. Task Decomposition - Break complex tasks into micro-tasks
3. Parallel Execution - Run hundreds of agents simultaneously
4. Result Aggregation - Synthesize outputs intelligently
5. Quality Forcing - Force agents to surpass thresholds
6. Competition Mode - Agents compete for best solution
7. Collaboration Mode - Agents build on each other's work
8. Swarm Intelligence - Emergent collective behavior
9. Self-Improvement - Agents learn from each other
10. Force Multiplier - Amplify output by 10-100x

Goal: Surpass Kimi 2.5 through sheer parallel genius.

"One agent is smart. A thousand are unstoppable."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.SWARM")


# ============================================================================
# ENUMS
# ============================================================================

class AgentRole(Enum):
    """Roles for micro-agents."""
    RESEARCHER = "researcher"  # Gather information
    ANALYZER = "analyzer"  # Analyze data
    SYNTHESIZER = "synthesizer"  # Combine insights
    CRITIC = "critic"  # Find flaws
    CREATOR = "creator"  # Generate solutions
    OPTIMIZER = "optimizer"  # Improve solutions
    VALIDATOR = "validator"  # Verify correctness
    SPECIALIST = "specialist"  # Domain expert


class SwarmMode(Enum):
    """Modes of swarm operation."""
    PARALLEL = "parallel"  # Independent parallel work
    SEQUENTIAL = "sequential"  # Chain of agents
    COMPETITIVE = "competitive"  # Agents compete
    COLLABORATIVE = "collaborative"  # Agents build together
    HIERARCHICAL = "hierarchical"  # Tree structure
    EVOLUTIONARY = "evolutionary"  # Survival of fittest


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"  # 1 agent
    SIMPLE = "simple"  # 2-3 agents
    MODERATE = "moderate"  # 5-10 agents
    COMPLEX = "complex"  # 20-50 agents
    MASSIVE = "massive"  # 100+ agents


class QualityLevel(Enum):
    """Quality thresholds."""
    MINIMUM = "minimum"  # Just acceptable
    GOOD = "good"  # Solid quality
    EXCELLENT = "excellent"  # High quality
    GENIUS = "genius"  # Exceptional
    TRANSCENDENT = "transcendent"  # Beyond expectations


class AgentStatus(Enum):
    """Status of micro-agent."""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MicroTask:
    """A micro-task for an agent."""
    id: str
    parent_task_id: Optional[str]
    description: str
    role_required: AgentRole
    priority: int  # 1-10
    dependencies: List[str]  # Task IDs this depends on
    inputs: Dict[str, Any]
    expected_output_type: str
    quality_threshold: float  # 0-1
    timeout_seconds: float = 30.0
    retries_allowed: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description[:50],
            "role": self.role_required.value,
            "priority": self.priority,
            "quality_threshold": self.quality_threshold
        }


@dataclass
class AgentOutput:
    """Output from a micro-agent."""
    task_id: str
    agent_id: str
    result: Any
    quality_score: float  # 0-1
    confidence: float  # 0-1
    reasoning: str
    execution_time_ms: float
    iteration: int  # Which attempt
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms
        }


@dataclass
class MicroAgent:
    """A micro-agent in the swarm."""
    id: str
    role: AgentRole
    specialization: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    average_quality: float = 0.0
    total_execution_time_ms: float = 0.0
    failures: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def update_stats(self, output: AgentOutput) -> None:
        """Update agent statistics."""
        self.tasks_completed += 1
        # Running average of quality
        self.average_quality = (
            (self.average_quality * (self.tasks_completed - 1) + output.quality_score)
            / self.tasks_completed
        )
        self.total_execution_time_ms += output.execution_time_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "specialization": self.specialization,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "average_quality": self.average_quality
        }


@dataclass
class SwarmConfig:
    """Configuration for a swarm."""
    mode: SwarmMode = SwarmMode.PARALLEL
    max_agents: int = 100
    quality_threshold: float = 0.7
    competition_rounds: int = 3
    enable_self_improvement: bool = True
    force_threshold: float = 0.8  # Force agents to reach this quality
    max_iterations: int = 5  # Max attempts to reach quality


@dataclass
class SwarmResult:
    """Result from swarm execution."""
    task_description: str
    mode: SwarmMode
    agents_used: int
    total_iterations: int
    final_output: Any
    quality_score: float
    execution_time_ms: float
    outputs: List[AgentOutput]
    best_agent_id: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task_description[:50],
            "mode": self.mode.value,
            "agents_used": self.agents_used,
            "iterations": self.total_iterations,
            "quality_score": self.quality_score,
            "execution_time_ms": self.execution_time_ms,
            "best_agent": self.best_agent_id
        }


# ============================================================================
# MICRO-AGENT ENGINE
# ============================================================================

class MicroAgentEngine:
    """
    Engine for spawning and managing micro-agents.
    
    Provides:
    - Agent lifecycle management
    - Specialized agent creation
    - Performance tracking
    """
    
    def __init__(self):
        self.agents: Dict[str, MicroAgent] = {}
        self.agent_pool: Dict[AgentRole, List[MicroAgent]] = defaultdict(list)
        
        # Agent templates for each role
        self.role_templates = {
            AgentRole.RESEARCHER: {
                "capabilities": ["search", "gather", "summarize"],
                "quality_weight": 0.8
            },
            AgentRole.ANALYZER: {
                "capabilities": ["analyze", "compare", "evaluate"],
                "quality_weight": 0.9
            },
            AgentRole.SYNTHESIZER: {
                "capabilities": ["combine", "integrate", "unify"],
                "quality_weight": 0.85
            },
            AgentRole.CRITIC: {
                "capabilities": ["critique", "identify_flaws", "suggest_improvements"],
                "quality_weight": 0.95
            },
            AgentRole.CREATOR: {
                "capabilities": ["generate", "innovate", "design"],
                "quality_weight": 0.7
            },
            AgentRole.OPTIMIZER: {
                "capabilities": ["optimize", "refine", "polish"],
                "quality_weight": 0.9
            },
            AgentRole.VALIDATOR: {
                "capabilities": ["validate", "verify", "test"],
                "quality_weight": 0.95
            },
            AgentRole.SPECIALIST: {
                "capabilities": ["domain_expertise", "deep_knowledge"],
                "quality_weight": 0.85
            }
        }
    
    def spawn_agent(
        self,
        role: AgentRole,
        specialization: str = "general"
    ) -> MicroAgent:
        """Spawn a new micro-agent."""
        agent = MicroAgent(
            id=hashlib.md5(f"{role.value}{time.time()}{random.random()}".encode()).hexdigest()[:12],
            role=role,
            specialization=specialization
        )
        
        self.agents[agent.id] = agent
        self.agent_pool[role].append(agent)
        
        return agent
    
    def get_available_agent(
        self,
        role: AgentRole
    ) -> Optional[MicroAgent]:
        """Get an available agent of the specified role."""
        for agent in self.agent_pool[role]:
            if agent.status == AgentStatus.IDLE:
                return agent
        
        # No available agent, spawn new one
        return self.spawn_agent(role)
    
    def release_agent(self, agent_id: str) -> None:
        """Release an agent back to the pool."""
        if agent_id in self.agents:
            self.agents[agent_id].status = AgentStatus.IDLE
            self.agents[agent_id].current_task = None
    
    def get_best_agent(self, role: AgentRole) -> Optional[MicroAgent]:
        """Get the best performing agent for a role."""
        role_agents = [a for a in self.agent_pool[role] if a.tasks_completed > 0]
        if not role_agents:
            return None
        return max(role_agents, key=lambda a: a.average_quality)
    
    async def execute_task(
        self,
        agent: MicroAgent,
        task: MicroTask,
        force_quality: float = 0.0
    ) -> AgentOutput:
        """Execute a task with an agent."""
        start_time = time.time()
        
        agent.status = AgentStatus.WORKING
        agent.current_task = task.id
        
        iteration = 0
        best_output = None
        
        while iteration < task.retries_allowed:
            iteration += 1
            
            # Simulate agent work (in production, this would call LLM)
            await asyncio.sleep(0.01)  # Simulate processing
            
            # Generate result based on role
            result = await self._simulate_agent_work(agent, task)
            
            # Calculate quality (in production, would use evaluator)
            quality = self._evaluate_quality(result, task)
            
            output = AgentOutput(
                task_id=task.id,
                agent_id=agent.id,
                result=result,
                quality_score=quality,
                confidence=min(quality + 0.1, 1.0),
                reasoning=f"{agent.role.value} analysis iteration {iteration}",
                execution_time_ms=(time.time() - start_time) * 1000,
                iteration=iteration
            )
            
            # Keep best output
            if best_output is None or output.quality_score > best_output.quality_score:
                best_output = output
            
            # Check if quality threshold met
            effective_threshold = max(task.quality_threshold, force_quality)
            if quality >= effective_threshold:
                break
            
            # Force agent to improve
            if force_quality > 0 and quality < force_quality:
                # Add pressure context for next iteration
                task.inputs["previous_quality"] = quality
                task.inputs["required_quality"] = force_quality
                task.inputs["feedback"] = "MUST IMPROVE - quality below threshold"
        
        agent.update_stats(best_output)
        agent.status = AgentStatus.COMPLETED
        
        return best_output
    
    async def _simulate_agent_work(
        self,
        agent: MicroAgent,
        task: MicroTask
    ) -> Dict[str, Any]:
        """Simulate agent work (in production, calls LLM)."""
        template = self.role_templates.get(agent.role, {})
        
        return {
            "type": task.expected_output_type,
            "content": f"[{agent.role.value}] Analysis of: {task.description[:50]}",
            "capabilities_used": template.get("capabilities", []),
            "specialization": agent.specialization,
            "task_id": task.id
        }
    
    def _evaluate_quality(
        self,
        result: Dict[str, Any],
        task: MicroTask
    ) -> float:
        """Evaluate output quality."""
        # In production, would use sophisticated evaluation
        base_quality = 0.6
        
        # Boost for correct type
        if result.get("type") == task.expected_output_type:
            base_quality += 0.1
        
        # Boost for content presence
        if result.get("content"):
            base_quality += 0.1
        
        # Random variance for simulation
        variance = random.uniform(-0.1, 0.2)
        
        return min(1.0, max(0.0, base_quality + variance))


# ============================================================================
# TASK DECOMPOSITION ENGINE
# ============================================================================

class TaskDecompositionEngine:
    """
    Decomposes complex tasks into micro-tasks.
    """
    
    def __init__(self):
        # Role assignment patterns
        self.role_patterns = {
            "research": AgentRole.RESEARCHER,
            "analyze": AgentRole.ANALYZER,
            "combine": AgentRole.SYNTHESIZER,
            "create": AgentRole.CREATOR,
            "review": AgentRole.CRITIC,
            "optimize": AgentRole.OPTIMIZER,
            "validate": AgentRole.VALIDATOR,
            "expert": AgentRole.SPECIALIST
        }
    
    def estimate_complexity(self, task_description: str) -> TaskComplexity:
        """Estimate task complexity."""
        length = len(task_description)
        
        # Simple heuristics
        complexity_keywords = {
            "comprehensive": 2,
            "analyze": 1,
            "compare": 1,
            "multiple": 2,
            "all": 2,
            "every": 2,
            "detailed": 1,
            "complex": 3,
            "entire": 2
        }
        
        score = 0
        for keyword, weight in complexity_keywords.items():
            if keyword in task_description.lower():
                score += weight
        
        if length > 500:
            score += 2
        if length > 200:
            score += 1
        
        if score >= 8:
            return TaskComplexity.MASSIVE
        elif score >= 5:
            return TaskComplexity.COMPLEX
        elif score >= 3:
            return TaskComplexity.MODERATE
        elif score >= 1:
            return TaskComplexity.SIMPLE
        else:
            return TaskComplexity.TRIVIAL
    
    def decompose(
        self,
        task_description: str,
        depth: int = 2
    ) -> List[MicroTask]:
        """Decompose a task into micro-tasks."""
        complexity = self.estimate_complexity(task_description)
        
        # Determine number of sub-tasks based on complexity
        task_counts = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 7,
            TaskComplexity.COMPLEX: 15,
            TaskComplexity.MASSIVE: 30
        }
        
        num_tasks = task_counts.get(complexity, 5)
        
        # Create task tree
        tasks = []
        parent_id = hashlib.md5(task_description.encode()).hexdigest()[:8]
        
        # Standard decomposition pattern
        phases = [
            ("Research phase", AgentRole.RESEARCHER, 0.6),
            ("Analysis phase", AgentRole.ANALYZER, 0.7),
            ("Critical review", AgentRole.CRITIC, 0.8),
            ("Synthesis", AgentRole.SYNTHESIZER, 0.75),
            ("Creation", AgentRole.CREATOR, 0.7),
            ("Optimization", AgentRole.OPTIMIZER, 0.85),
            ("Validation", AgentRole.VALIDATOR, 0.9)
        ]
        
        for i, (phase_name, role, quality) in enumerate(phases[:min(num_tasks, len(phases))]):
            task = MicroTask(
                id=f"{parent_id}_{i}",
                parent_task_id=parent_id if i > 0 else None,
                description=f"{phase_name}: {task_description[:100]}",
                role_required=role,
                priority=10 - i,
                dependencies=[f"{parent_id}_{i-1}"] if i > 0 else [],
                inputs={"original_task": task_description},
                expected_output_type="analysis",
                quality_threshold=quality
            )
            tasks.append(task)
        
        # Add specialist tasks for complex problems
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.MASSIVE]:
            specialist_tasks = self._create_specialist_tasks(
                task_description, parent_id, len(tasks)
            )
            tasks.extend(specialist_tasks)
        
        return tasks
    
    def _create_specialist_tasks(
        self,
        task_description: str,
        parent_id: str,
        start_index: int
    ) -> List[MicroTask]:
        """Create specialist sub-tasks."""
        specialists = [
            "domain_expert",
            "technical_specialist",
            "edge_case_analyst"
        ]
        
        tasks = []
        for i, spec in enumerate(specialists):
            task = MicroTask(
                id=f"{parent_id}_spec_{i}",
                parent_task_id=parent_id,
                description=f"Specialist analysis ({spec}): {task_description[:50]}",
                role_required=AgentRole.SPECIALIST,
                priority=5,
                dependencies=[],
                inputs={"specialization": spec, "original_task": task_description},
                expected_output_type="specialist_insight",
                quality_threshold=0.8
            )
            tasks.append(task)
        
        return tasks


# ============================================================================
# SWARM ORCHESTRATOR
# ============================================================================

class SwarmOrchestrator:
    """
    Orchestrates micro-agent swarms for complex tasks.
    
    The core of the force multiplier - coordinates hundreds
    of agents working in parallel to produce genius output.
    """
    
    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self.agent_engine = MicroAgentEngine()
        self.decomposition_engine = TaskDecompositionEngine()
        self.execution_history: List[SwarmResult] = []
        
        logger.info(f"SwarmOrchestrator initialized with mode: {self.config.mode.value}")
    
    # -------------------------------------------------------------------------
    # MAIN EXECUTION
    # -------------------------------------------------------------------------
    
    async def execute(
        self,
        task_description: str,
        mode: SwarmMode = None,
        quality_level: QualityLevel = QualityLevel.EXCELLENT
    ) -> SwarmResult:
        """Execute a task with the swarm."""
        start_time = time.time()
        mode = mode or self.config.mode
        
        # Set quality threshold based on level
        quality_thresholds = {
            QualityLevel.MINIMUM: 0.5,
            QualityLevel.GOOD: 0.65,
            QualityLevel.EXCELLENT: 0.8,
            QualityLevel.GENIUS: 0.9,
            QualityLevel.TRANSCENDENT: 0.95
        }
        force_quality = quality_thresholds.get(quality_level, 0.8)
        
        # Decompose task
        micro_tasks = self.decomposition_engine.decompose(task_description)
        
        # Execute based on mode
        if mode == SwarmMode.PARALLEL:
            outputs = await self._execute_parallel(micro_tasks, force_quality)
        elif mode == SwarmMode.SEQUENTIAL:
            outputs = await self._execute_sequential(micro_tasks, force_quality)
        elif mode == SwarmMode.COMPETITIVE:
            outputs = await self._execute_competitive(micro_tasks, force_quality)
        elif mode == SwarmMode.COLLABORATIVE:
            outputs = await self._execute_collaborative(micro_tasks, force_quality)
        elif mode == SwarmMode.HIERARCHICAL:
            outputs = await self._execute_hierarchical(micro_tasks, force_quality)
        elif mode == SwarmMode.EVOLUTIONARY:
            outputs = await self._execute_evolutionary(micro_tasks, force_quality)
        else:
            outputs = await self._execute_parallel(micro_tasks, force_quality)
        
        # Aggregate results
        final_output, quality_score, best_agent = self._aggregate_outputs(outputs)
        
        # Create result
        result = SwarmResult(
            task_description=task_description,
            mode=mode,
            agents_used=len(set(o.agent_id for o in outputs)),
            total_iterations=sum(o.iteration for o in outputs),
            final_output=final_output,
            quality_score=quality_score,
            execution_time_ms=(time.time() - start_time) * 1000,
            outputs=outputs,
            best_agent_id=best_agent,
            metadata={
                "micro_tasks": len(micro_tasks),
                "quality_level": quality_level.value,
                "force_threshold": force_quality
            }
        )
        
        self.execution_history.append(result)
        
        return result
    
    # -------------------------------------------------------------------------
    # EXECUTION MODES
    # -------------------------------------------------------------------------
    
    async def _execute_parallel(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Execute all tasks in parallel."""
        async def run_task(task: MicroTask) -> AgentOutput:
            agent = self.agent_engine.get_available_agent(task.role_required)
            return await self.agent_engine.execute_task(agent, task, force_quality)
        
        outputs = await asyncio.gather(*[run_task(t) for t in tasks])
        return list(outputs)
    
    async def _execute_sequential(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Execute tasks sequentially, passing context."""
        outputs = []
        context = {}
        
        for task in tasks:
            # Add previous outputs as context
            task.inputs["previous_outputs"] = context
            
            agent = self.agent_engine.get_available_agent(task.role_required)
            output = await self.agent_engine.execute_task(agent, task, force_quality)
            outputs.append(output)
            
            # Update context
            context[task.id] = output.result
        
        return outputs
    
    async def _execute_competitive(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Multiple agents compete for best solution."""
        all_outputs = []
        
        for task in tasks:
            # Spawn multiple competing agents
            competitors = self.config.competition_rounds
            competing_outputs = []
            
            for _ in range(competitors):
                agent = self.agent_engine.spawn_agent(task.role_required)
                output = await self.agent_engine.execute_task(agent, task, force_quality)
                competing_outputs.append(output)
            
            # Keep only the best
            best = max(competing_outputs, key=lambda o: o.quality_score)
            all_outputs.append(best)
        
        return all_outputs
    
    async def _execute_collaborative(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Agents build on each other's work."""
        outputs = []
        accumulated_knowledge = []
        
        for task in tasks:
            # Share accumulated knowledge
            task.inputs["accumulated_knowledge"] = accumulated_knowledge
            
            agent = self.agent_engine.get_available_agent(task.role_required)
            output = await self.agent_engine.execute_task(agent, task, force_quality)
            outputs.append(output)
            
            # Accumulate knowledge
            accumulated_knowledge.append({
                "task_id": task.id,
                "role": task.role_required.value,
                "insight": output.result
            })
        
        return outputs
    
    async def _execute_hierarchical(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Tree structure execution."""
        outputs = []
        
        # Group tasks by dependency level
        levels: Dict[int, List[MicroTask]] = defaultdict(list)
        for task in tasks:
            level = len(task.dependencies)
            levels[level].append(task)
        
        # Execute level by level
        level_results: Dict[str, Any] = {}
        for level in sorted(levels.keys()):
            level_tasks = levels[level]
            
            # Inject dependency results
            for task in level_tasks:
                task.inputs["dependency_results"] = {
                    dep_id: level_results.get(dep_id)
                    for dep_id in task.dependencies
                }
            
            # Execute level in parallel
            level_outputs = await asyncio.gather(*[
                self.agent_engine.execute_task(
                    self.agent_engine.get_available_agent(t.role_required),
                    t,
                    force_quality
                )
                for t in level_tasks
            ])
            
            for output in level_outputs:
                outputs.append(output)
                level_results[output.task_id] = output.result
        
        return outputs
    
    async def _execute_evolutionary(
        self,
        tasks: List[MicroTask],
        force_quality: float
    ) -> List[AgentOutput]:
        """Survival of the fittest approach."""
        all_outputs = []
        
        for task in tasks:
            generation = 0
            population_size = 5
            best_ever = None
            
            while generation < self.config.max_iterations:
                generation += 1
                
                # Generate population
                population = []
                for _ in range(population_size):
                    agent = self.agent_engine.spawn_agent(task.role_required)
                    output = await self.agent_engine.execute_task(agent, task, force_quality)
                    population.append(output)
                
                # Select best
                best = max(population, key=lambda o: o.quality_score)
                
                if best_ever is None or best.quality_score > best_ever.quality_score:
                    best_ever = best
                
                # Check if good enough
                if best.quality_score >= force_quality:
                    break
                
                # Evolve - increase pressure
                task.inputs["evolution_generation"] = generation
                task.inputs["best_score_so_far"] = best.quality_score
                population_size = min(population_size + 2, 10)  # Grow population
            
            all_outputs.append(best_ever)
        
        return all_outputs
    
    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------
    
    def _aggregate_outputs(
        self,
        outputs: List[AgentOutput]
    ) -> Tuple[Dict[str, Any], float, Optional[str]]:
        """Aggregate outputs from all agents."""
        if not outputs:
            return {}, 0.0, None
        
        # Collect results by role
        by_role: Dict[str, List[AgentOutput]] = defaultdict(list)
        for output in outputs:
            if output.task_id in self.agent_engine.agents:
                agent = self.agent_engine.agents[output.agent_id]
                by_role[agent.role.value].append(output)
        
        # Find best agent
        best_output = max(outputs, key=lambda o: o.quality_score)
        
        # Calculate weighted average quality
        total_quality = sum(o.quality_score * o.confidence for o in outputs)
        total_confidence = sum(o.confidence for o in outputs)
        avg_quality = total_quality / total_confidence if total_confidence > 0 else 0
        
        # Synthesize final output
        final_output = {
            "summary": f"Aggregated from {len(outputs)} agent outputs",
            "best_result": best_output.result,
            "all_results": [o.result for o in outputs],
            "quality_breakdown": {
                role: sum(o.quality_score for o in role_outputs) / len(role_outputs)
                for role, role_outputs in by_role.items()
            },
            "confidence": avg_quality
        }
        
        return final_output, avg_quality, best_output.agent_id
    
    # -------------------------------------------------------------------------
    # FORCE MULTIPLIER
    # -------------------------------------------------------------------------
    
    async def force_multiply(
        self,
        task_description: str,
        target_quality: float = 0.9,
        max_agents: int = 100
    ) -> SwarmResult:
        """
        Force multiply to achieve target quality.
        
        Throws more agents at the problem until quality is achieved.
        """
        logger.info(f"Force multiplying for quality {target_quality} with max {max_agents} agents")
        
        best_result = None
        agents_used = 0
        
        # Start with small swarm, scale up
        swarm_sizes = [5, 10, 25, 50, 100]
        
        for size in swarm_sizes:
            if size > max_agents:
                break
            
            # Configure for this iteration
            self.config.max_agents = size
            self.config.force_threshold = target_quality
            
            result = await self.execute(
                task_description,
                mode=SwarmMode.COMPETITIVE,
                quality_level=QualityLevel.GENIUS
            )
            
            agents_used += result.agents_used
            
            if best_result is None or result.quality_score > best_result.quality_score:
                best_result = result
            
            if result.quality_score >= target_quality:
                logger.info(f"Target quality achieved with {agents_used} agents")
                break
        
        return best_result
    
    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------
    
    def get_swarm_stats(self) -> Dict[str, Any]:
        """Get statistics about swarm performance."""
        if not self.execution_history:
            return {"message": "No executions yet"}
        
        return {
            "total_executions": len(self.execution_history),
            "total_agents_spawned": len(self.agent_engine.agents),
            "avg_quality": sum(r.quality_score for r in self.execution_history) / len(self.execution_history),
            "avg_execution_time_ms": sum(r.execution_time_ms for r in self.execution_history) / len(self.execution_history),
            "best_quality": max(r.quality_score for r in self.execution_history),
            "modes_used": list(set(r.mode.value for r in self.execution_history)),
            "agent_pool_by_role": {
                role.value: len(agents)
                for role, agents in self.agent_engine.agent_pool.items()
            }
        }


# ============================================================================
# SINGLETON
# ============================================================================

_swarm_orchestrator: Optional[SwarmOrchestrator] = None


def get_swarm_orchestrator(config: SwarmConfig = None) -> SwarmOrchestrator:
    """Get the global swarm orchestrator."""
    global _swarm_orchestrator
    if _swarm_orchestrator is None:
        _swarm_orchestrator = SwarmOrchestrator(config)
    return _swarm_orchestrator


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate micro-agent swarm."""
    print("=" * 60)
    print("MICRO-AGENT SWARM FORCE MULTIPLIER")
    print("=" * 60)
    
    config = SwarmConfig(
        mode=SwarmMode.COLLABORATIVE,
        max_agents=50,
        quality_threshold=0.8,
        competition_rounds=3,
        enable_self_improvement=True
    )
    
    orchestrator = get_swarm_orchestrator(config)
    
    # Test different modes
    test_task = "Analyze the competitive landscape for AI assistants and provide strategic recommendations"
    
    print("\n--- Parallel Execution ---")
    result = await orchestrator.execute(
        test_task,
        mode=SwarmMode.PARALLEL,
        quality_level=QualityLevel.EXCELLENT
    )
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n--- Competitive Execution ---")
    result = await orchestrator.execute(
        test_task,
        mode=SwarmMode.COMPETITIVE,
        quality_level=QualityLevel.GENIUS
    )
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n--- Collaborative Execution ---")
    result = await orchestrator.execute(
        test_task,
        mode=SwarmMode.COLLABORATIVE,
        quality_level=QualityLevel.EXCELLENT
    )
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n--- Evolutionary Execution ---")
    result = await orchestrator.execute(
        test_task,
        mode=SwarmMode.EVOLUTIONARY,
        quality_level=QualityLevel.TRANSCENDENT
    )
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n--- Force Multiplier ---")
    result = await orchestrator.force_multiply(
        "Create the ultimate AI strategy document",
        target_quality=0.95,
        max_agents=100
    )
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n--- Swarm Statistics ---")
    stats = orchestrator.get_swarm_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n" + "=" * 60)
    print("SWARM DEMONSTRATION COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
