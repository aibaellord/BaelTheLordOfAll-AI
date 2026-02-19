"""
BA'EL SUPREME ORCHESTRATOR - Ultimate Master Control Layer
The god-tier orchestration system that coordinates all Ba'el subsystems.

This is THE central nervous system of Ba'el - it:
1. Routes all requests to optimal subsystems
2. Orchestrates multi-system workflows
3. Manages resource allocation
4. Coordinates agent swarms
5. Handles failover and redundancy
6. Optimizes for zero-cost operation
7. Learns from every interaction
8. Evolves strategies over time
9. Maintains global state coherence
10. Achieves superhuman coordination

All roads lead here. All power flows through here.
Ba'el the Lord of All - Supreme Orchestrator
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from collections import defaultdict
import threading

logger = logging.getLogger("BAEL.SupremeOrchestrator")

# ============================================================================
# ORCHESTRATION ENUMS
# ============================================================================

class SystemDomain(Enum):
    """Major system domains in Ba'el."""
    INTELLIGENCE = "intelligence"
    AUTOMATION = "automation"
    AGENTS = "agents"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    TOOLS = "tools"
    INTEGRATION = "integration"
    SECURITY = "security"
    OPTIMIZATION = "optimization"
    CREATIVITY = "creativity"
    ANALYSIS = "analysis"
    EXECUTION = "execution"

class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5

class ExecutionMode(Enum):
    """Execution modes for tasks."""
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    STREAMING = "streaming"
    BATCH = "batch"

class ResourceType(Enum):
    """Types of resources managed."""
    LLM = "llm"
    COMPUTE = "compute"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    AGENT = "agent"
    API = "api"

# ============================================================================
# SUBSYSTEM REGISTRY
# ============================================================================

@dataclass
class SubsystemInfo:
    """Information about a registered subsystem."""
    subsystem_id: str
    name: str
    domain: SystemDomain
    capabilities: List[str]
    priority: int = 5
    is_active: bool = True
    health_score: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    successful_requests: int = 0
    avg_latency_ms: float = 0.0

    def get_success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

class SubsystemRegistry:
    """Registry of all Ba'el subsystems."""

    def __init__(self):
        self.subsystems: Dict[str, SubsystemInfo] = {}
        self.by_domain: Dict[SystemDomain, List[str]] = defaultdict(list)
        self.by_capability: Dict[str, List[str]] = defaultdict(list)

    def register(self, info: SubsystemInfo) -> None:
        """Register a subsystem."""
        self.subsystems[info.subsystem_id] = info
        self.by_domain[info.domain].append(info.subsystem_id)

        for cap in info.capabilities:
            self.by_capability[cap].append(info.subsystem_id)

        logger.info(f"Registered subsystem: {info.name} ({info.subsystem_id})")

    def unregister(self, subsystem_id: str) -> None:
        """Unregister a subsystem."""
        if subsystem_id in self.subsystems:
            info = self.subsystems[subsystem_id]
            self.by_domain[info.domain].remove(subsystem_id)

            for cap in info.capabilities:
                self.by_capability[cap].remove(subsystem_id)

            del self.subsystems[subsystem_id]

    def get_by_capability(self, capability: str) -> List[SubsystemInfo]:
        """Get subsystems with a capability."""
        subsystem_ids = self.by_capability.get(capability, [])
        return [self.subsystems[sid] for sid in subsystem_ids if sid in self.subsystems]

    def get_by_domain(self, domain: SystemDomain) -> List[SubsystemInfo]:
        """Get subsystems in a domain."""
        subsystem_ids = self.by_domain.get(domain, [])
        return [self.subsystems[sid] for sid in subsystem_ids if sid in self.subsystems]

    def get_best_for_capability(self, capability: str) -> Optional[SubsystemInfo]:
        """Get best subsystem for a capability."""
        candidates = self.get_by_capability(capability)

        if not candidates:
            return None

        # Sort by health, success rate, and latency
        candidates.sort(key=lambda s: (
            s.is_active,
            s.health_score,
            s.get_success_rate(),
            -s.avg_latency_ms
        ), reverse=True)

        return candidates[0]

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

@dataclass
class OrchestrationTask:
    """A task to be orchestrated."""
    task_id: str
    name: str
    description: str
    input_data: Dict[str, Any]
    required_capabilities: List[str]
    priority: TaskPriority = TaskPriority.MEDIUM
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    timeout_seconds: float = 30.0
    retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    # Execution state
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

@dataclass
class Workflow:
    """A multi-step workflow."""
    workflow_id: str
    name: str
    description: str
    steps: List[OrchestrationTask]
    parallel_groups: List[List[int]] = field(default_factory=list)
    dependencies: Dict[int, List[int]] = field(default_factory=dict)

    # State
    status: str = "pending"
    current_step: int = 0
    results: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# RESOURCE MANAGER
# ============================================================================

@dataclass
class ResourceAllocation:
    """An allocation of resources."""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    holder: str
    expires_at: Optional[datetime] = None

class ResourceManager:
    """Manages resource allocation."""

    def __init__(self):
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.resource_limits: Dict[ResourceType, float] = {
            ResourceType.LLM: 10.0,  # concurrent requests
            ResourceType.COMPUTE: 100.0,  # percentage
            ResourceType.MEMORY: 8192.0,  # MB
            ResourceType.AGENT: 50.0,  # max agents
            ResourceType.API: 100.0,  # concurrent calls
        }
        self.resource_usage: Dict[ResourceType, float] = defaultdict(float)

    def allocate(self,
                resource_type: ResourceType,
                amount: float,
                holder: str,
                duration_seconds: float = 60.0) -> Optional[ResourceAllocation]:
        """Allocate resources."""
        current = self.resource_usage[resource_type]
        limit = self.resource_limits.get(resource_type, float('inf'))

        if current + amount > limit:
            logger.warning(f"Resource limit exceeded for {resource_type.value}")
            return None

        allocation = ResourceAllocation(
            allocation_id=str(uuid.uuid4()),
            resource_type=resource_type,
            amount=amount,
            holder=holder,
            expires_at=datetime.now() + timedelta(seconds=duration_seconds)
        )

        self.allocations[allocation.allocation_id] = allocation
        self.resource_usage[resource_type] += amount

        return allocation

    def release(self, allocation_id: str) -> None:
        """Release resources."""
        if allocation_id in self.allocations:
            allocation = self.allocations[allocation_id]
            self.resource_usage[allocation.resource_type] -= allocation.amount
            del self.allocations[allocation_id]

    def cleanup_expired(self) -> None:
        """Clean up expired allocations."""
        now = datetime.now()
        expired = [
            aid for aid, alloc in self.allocations.items()
            if alloc.expires_at and alloc.expires_at < now
        ]

        for allocation_id in expired:
            self.release(allocation_id)

    def get_availability(self, resource_type: ResourceType) -> float:
        """Get available capacity."""
        limit = self.resource_limits.get(resource_type, float('inf'))
        current = self.resource_usage[resource_type]
        return max(0, limit - current)

# ============================================================================
# TASK ROUTER
# ============================================================================

class TaskRouter:
    """Routes tasks to appropriate subsystems."""

    def __init__(self, registry: SubsystemRegistry):
        self.registry = registry
        self.routing_history: List[Dict[str, Any]] = []
        self.learned_routes: Dict[str, str] = {}

    def route(self, task: OrchestrationTask) -> Optional[SubsystemInfo]:
        """Route a task to the best subsystem."""
        # Check learned routes first
        task_type = task.metadata.get("task_type", task.name)
        if task_type in self.learned_routes:
            subsystem_id = self.learned_routes[task_type]
            if subsystem_id in self.registry.subsystems:
                return self.registry.subsystems[subsystem_id]

        # Find based on capabilities
        for capability in task.required_capabilities:
            subsystem = self.registry.get_best_for_capability(capability)
            if subsystem:
                return subsystem

        # Fallback to any available subsystem
        for domain in SystemDomain:
            subsystems = self.registry.get_by_domain(domain)
            if subsystems:
                return subsystems[0]

        return None

    def record_routing(self, task: OrchestrationTask,
                      subsystem_id: str, success: bool) -> None:
        """Record routing outcome for learning."""
        self.routing_history.append({
            "task_type": task.metadata.get("task_type", task.name),
            "capabilities": task.required_capabilities,
            "subsystem_id": subsystem_id,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

        # Update learned routes
        if success:
            task_type = task.metadata.get("task_type", task.name)
            self.learned_routes[task_type] = subsystem_id

# ============================================================================
# WORKFLOW ENGINE
# ============================================================================

class WorkflowEngine:
    """Executes multi-step workflows."""

    def __init__(self, router: TaskRouter, resource_manager: ResourceManager):
        self.router = router
        self.resource_manager = resource_manager
        self.active_workflows: Dict[str, Workflow] = {}

    async def execute(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute a workflow."""
        workflow.status = "running"
        self.active_workflows[workflow.workflow_id] = workflow

        try:
            if workflow.parallel_groups:
                # Execute with parallel groups
                results = await self._execute_parallel_groups(workflow)
            else:
                # Execute sequentially
                results = await self._execute_sequential(workflow)

            workflow.status = "completed"
            workflow.results = results
            return results

        except Exception as e:
            workflow.status = "failed"
            workflow.results = {"error": str(e)}
            raise

        finally:
            del self.active_workflows[workflow.workflow_id]

    async def _execute_sequential(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute steps sequentially."""
        results = {}

        for i, step in enumerate(workflow.steps):
            workflow.current_step = i
            result = await self._execute_step(step, results)
            results[step.task_id] = result

        return results

    async def _execute_parallel_groups(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute with parallel groups."""
        results = {}

        for group in workflow.parallel_groups:
            # Execute group in parallel
            tasks = [
                self._execute_step(workflow.steps[i], results)
                for i in group
            ]

            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in zip(group, group_results):
                step = workflow.steps[i]
                if isinstance(result, Exception):
                    results[step.task_id] = {"error": str(result)}
                else:
                    results[step.task_id] = result

        return results

    async def _execute_step(self, task: OrchestrationTask,
                           previous_results: Dict[str, Any]) -> Any:
        """Execute a single workflow step."""
        # Inject previous results if needed
        task.input_data["previous_results"] = previous_results

        # Route to subsystem
        subsystem = self.router.route(task)

        if not subsystem:
            raise ValueError(f"No subsystem found for task: {task.name}")

        # Allocate resources
        allocation = self.resource_manager.allocate(
            ResourceType.COMPUTE,
            1.0,
            task.task_id,
            task.timeout_seconds
        )

        try:
            task.status = "running"
            task.started_at = datetime.now()

            # Execute (placeholder - in production would call actual subsystem)
            result = await self._invoke_subsystem(subsystem, task)

            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result

            self.router.record_routing(task, subsystem.subsystem_id, True)

            return result

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.router.record_routing(task, subsystem.subsystem_id, False)
            raise

        finally:
            if allocation:
                self.resource_manager.release(allocation.allocation_id)

    async def _invoke_subsystem(self, subsystem: SubsystemInfo,
                               task: OrchestrationTask) -> Any:
        """Invoke a subsystem to execute a task."""
        # In production, this would actually call the subsystem
        # For now, simulate execution
        await asyncio.sleep(0.1)

        return {
            "subsystem": subsystem.name,
            "task": task.name,
            "status": "success"
        }

# ============================================================================
# AGENT COORDINATOR
# ============================================================================

class AgentCoordinator:
    """Coordinates agent swarms."""

    def __init__(self, resource_manager: ResourceManager):
        self.resource_manager = resource_manager
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_pools: Dict[str, List[str]] = defaultdict(list)

    async def spawn_agents(self,
                          agent_type: str,
                          count: int,
                          config: Dict[str, Any] = None) -> List[str]:
        """Spawn a group of agents."""
        agent_ids = []

        for i in range(count):
            allocation = self.resource_manager.allocate(
                ResourceType.AGENT,
                1.0,
                f"agent-{agent_type}-{i}"
            )

            if not allocation:
                logger.warning(f"Could not allocate agent {i}")
                continue

            agent_id = str(uuid.uuid4())

            self.active_agents[agent_id] = {
                "type": agent_type,
                "config": config or {},
                "allocation_id": allocation.allocation_id,
                "status": "active",
                "spawned_at": datetime.now()
            }

            self.agent_pools[agent_type].append(agent_id)
            agent_ids.append(agent_id)

        return agent_ids

    async def terminate_agent(self, agent_id: str) -> None:
        """Terminate an agent."""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            self.resource_manager.release(agent["allocation_id"])

            agent_type = agent["type"]
            if agent_id in self.agent_pools[agent_type]:
                self.agent_pools[agent_type].remove(agent_id)

            del self.active_agents[agent_id]

    async def assign_task(self,
                         agent_type: str,
                         task: Dict[str, Any]) -> Optional[str]:
        """Assign a task to an available agent."""
        pool = self.agent_pools.get(agent_type, [])

        for agent_id in pool:
            agent = self.active_agents.get(agent_id)
            if agent and agent["status"] == "active":
                agent["status"] = "busy"
                agent["current_task"] = task
                return agent_id

        return None

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about agent pools."""
        stats = {}

        for agent_type, pool in self.agent_pools.items():
            active = sum(
                1 for aid in pool
                if self.active_agents.get(aid, {}).get("status") == "active"
            )
            busy = sum(
                1 for aid in pool
                if self.active_agents.get(aid, {}).get("status") == "busy"
            )

            stats[agent_type] = {
                "total": len(pool),
                "active": active,
                "busy": busy
            }

        return stats

# ============================================================================
# FAILOVER MANAGER
# ============================================================================

class FailoverManager:
    """Manages failover and redundancy."""

    def __init__(self, registry: SubsystemRegistry):
        self.registry = registry
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}

    def record_failure(self, subsystem_id: str) -> None:
        """Record a subsystem failure."""
        self.failure_counts[subsystem_id] += 1

        # Check for circuit breaker
        if self.failure_counts[subsystem_id] >= 3:
            self._open_circuit(subsystem_id)

    def record_success(self, subsystem_id: str) -> None:
        """Record a subsystem success."""
        self.failure_counts[subsystem_id] = 0

        # Close circuit if open
        if subsystem_id in self.circuit_breakers:
            self._close_circuit(subsystem_id)

    def _open_circuit(self, subsystem_id: str) -> None:
        """Open circuit breaker for subsystem."""
        self.circuit_breakers[subsystem_id] = {
            "opened_at": datetime.now(),
            "retry_after": datetime.now() + timedelta(seconds=30)
        }

        # Mark subsystem as inactive
        if subsystem_id in self.registry.subsystems:
            self.registry.subsystems[subsystem_id].is_active = False

        logger.warning(f"Circuit opened for {subsystem_id}")

    def _close_circuit(self, subsystem_id: str) -> None:
        """Close circuit breaker for subsystem."""
        del self.circuit_breakers[subsystem_id]

        # Mark subsystem as active
        if subsystem_id in self.registry.subsystems:
            self.registry.subsystems[subsystem_id].is_active = True

        logger.info(f"Circuit closed for {subsystem_id}")

    def get_fallback(self, failed_subsystem_id: str) -> Optional[SubsystemInfo]:
        """Get fallback subsystem."""
        if failed_subsystem_id not in self.registry.subsystems:
            return None

        failed = self.registry.subsystems[failed_subsystem_id]

        # Find alternative with same capabilities
        for cap in failed.capabilities:
            alternatives = self.registry.get_by_capability(cap)
            for alt in alternatives:
                if alt.subsystem_id != failed_subsystem_id and alt.is_active:
                    return alt

        return None

# ============================================================================
# SUPREME ORCHESTRATOR
# ============================================================================

class SupremeOrchestrator:
    """The supreme orchestrator of all Ba'el systems."""

    def __init__(self):
        self.registry = SubsystemRegistry()
        self.resource_manager = ResourceManager()
        self.router = TaskRouter(self.registry)
        self.workflow_engine = WorkflowEngine(self.router, self.resource_manager)
        self.agent_coordinator = AgentCoordinator(self.resource_manager)
        self.failover_manager = FailoverManager(self.registry)

        # State
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.task_count = 0
        self.success_count = 0

    async def start(self) -> None:
        """Start the supreme orchestrator."""
        self.is_running = True
        self.start_time = datetime.now()

        # Register core subsystems
        self._register_core_subsystems()

        # Start background tasks
        asyncio.create_task(self._health_monitor())
        asyncio.create_task(self._resource_cleanup())

        logger.info("Supreme Orchestrator started")

    async def stop(self) -> None:
        """Stop the supreme orchestrator."""
        self.is_running = False
        logger.info("Supreme Orchestrator stopped")

    def _register_core_subsystems(self) -> None:
        """Register core Ba'el subsystems."""
        core_subsystems = [
            SubsystemInfo(
                subsystem_id="free-llm-hub",
                name="Free LLM Multi-Provider Hub",
                domain=SystemDomain.INTELLIGENCE,
                capabilities=["llm", "reasoning", "generation", "long_context"]
            ),
            SubsystemInfo(
                subsystem_id="micro-agent-genesis",
                name="Micro-Agent Genesis Engine",
                domain=SystemDomain.AGENTS,
                capabilities=["agent_spawning", "swarm", "evolution"]
            ),
            SubsystemInfo(
                subsystem_id="zero-invest-engine",
                name="Zero-Invest Genius Engine",
                domain=SystemDomain.OPTIMIZATION,
                capabilities=["resource_discovery", "cost_optimization", "free_apis"]
            ),
            SubsystemInfo(
                subsystem_id="infinite-genius",
                name="Infinite Genius Engine",
                domain=SystemDomain.INTELLIGENCE,
                capabilities=["deep_thinking", "quality_escalation", "meta_cognition"]
            ),
            SubsystemInfo(
                subsystem_id="council-of-councils",
                name="Supreme Council",
                domain=SystemDomain.AGENTS,
                capabilities=["consensus", "deliberation", "wisdom"]
            ),
            SubsystemInfo(
                subsystem_id="knowledge-graph",
                name="Knowledge Graph Engine",
                domain=SystemDomain.KNOWLEDGE,
                capabilities=["knowledge_storage", "reasoning", "inference"]
            ),
            SubsystemInfo(
                subsystem_id="memory-system",
                name="Unified Memory System",
                domain=SystemDomain.MEMORY,
                capabilities=["short_term", "long_term", "episodic", "semantic"]
            ),
            SubsystemInfo(
                subsystem_id="tool-registry",
                name="Tool Registry",
                domain=SystemDomain.TOOLS,
                capabilities=["tool_discovery", "tool_execution", "mcp"]
            ),
        ]

        for subsystem in core_subsystems:
            self.registry.register(subsystem)

    async def _health_monitor(self) -> None:
        """Monitor subsystem health."""
        while self.is_running:
            await asyncio.sleep(10)

            for subsystem_id, subsystem in self.registry.subsystems.items():
                # Check heartbeat
                if datetime.now() - subsystem.last_heartbeat > timedelta(seconds=60):
                    subsystem.health_score *= 0.9

                # Update health based on success rate
                subsystem.health_score = (
                    0.7 * subsystem.health_score +
                    0.3 * subsystem.get_success_rate()
                )

    async def _resource_cleanup(self) -> None:
        """Periodically clean up resources."""
        while self.is_running:
            await asyncio.sleep(30)
            self.resource_manager.cleanup_expired()

    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a request through the orchestrator."""
        self.task_count += 1

        try:
            # Determine request type
            request_type = request.get("type", "task")

            if request_type == "workflow":
                result = await self._execute_workflow(request)
            elif request_type == "agent_task":
                result = await self._execute_agent_task(request)
            else:
                result = await self._execute_simple_task(request)

            self.success_count += 1
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {"status": "error", "error": str(e)}

    async def _execute_simple_task(self, request: Dict[str, Any]) -> Any:
        """Execute a simple task."""
        task = OrchestrationTask(
            task_id=str(uuid.uuid4()),
            name=request.get("name", "unnamed"),
            description=request.get("description", ""),
            input_data=request.get("input", {}),
            required_capabilities=request.get("capabilities", [])
        )

        subsystem = self.router.route(task)

        if not subsystem:
            raise ValueError("No subsystem available")

        # Execute
        result = await self.workflow_engine._invoke_subsystem(subsystem, task)

        return result

    async def _execute_workflow(self, request: Dict[str, Any]) -> Any:
        """Execute a workflow."""
        steps = []
        for i, step_data in enumerate(request.get("steps", [])):
            step = OrchestrationTask(
                task_id=f"step-{i}",
                name=step_data.get("name", f"Step {i}"),
                description=step_data.get("description", ""),
                input_data=step_data.get("input", {}),
                required_capabilities=step_data.get("capabilities", [])
            )
            steps.append(step)

        workflow = Workflow(
            workflow_id=str(uuid.uuid4()),
            name=request.get("name", "unnamed workflow"),
            description=request.get("description", ""),
            steps=steps
        )

        return await self.workflow_engine.execute(workflow)

    async def _execute_agent_task(self, request: Dict[str, Any]) -> Any:
        """Execute a task using agents."""
        agent_type = request.get("agent_type", "general")
        agent_count = request.get("agent_count", 3)

        # Spawn agents
        agent_ids = await self.agent_coordinator.spawn_agents(
            agent_type, agent_count, request.get("config")
        )

        try:
            # Assign tasks
            results = []
            task = request.get("task", {})

            for agent_id in agent_ids:
                result = await self.agent_coordinator.assign_task(agent_type, task)
                results.append(result)

            return {"agents_used": len(agent_ids), "results": results}

        finally:
            # Cleanup agents
            for agent_id in agent_ids:
                await self.agent_coordinator.terminate_agent(agent_id)

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "is_running": self.is_running,
            "uptime_seconds": uptime,
            "task_count": self.task_count,
            "success_count": self.success_count,
            "success_rate": self.success_count / max(self.task_count, 1),
            "subsystem_count": len(self.registry.subsystems),
            "active_agents": len(self.agent_coordinator.active_agents),
            "resource_usage": dict(self.resource_manager.resource_usage),
            "agent_pools": self.agent_coordinator.get_pool_stats()
        }

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_supreme_orchestrator() -> SupremeOrchestrator:
    """Create the supreme orchestrator."""
    return SupremeOrchestrator()

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """Example usage of the supreme orchestrator."""
    orchestrator = create_supreme_orchestrator()

    try:
        await orchestrator.start()

        # Execute a simple task
        result = await orchestrator.execute({
            "type": "task",
            "name": "test_task",
            "description": "A test task",
            "capabilities": ["llm", "reasoning"],
            "input": {"prompt": "Hello, Ba'el!"}
        })

        print(f"Task result: {json.dumps(result, indent=2)}")

        # Execute a workflow
        workflow_result = await orchestrator.execute({
            "type": "workflow",
            "name": "test_workflow",
            "steps": [
                {"name": "Research", "capabilities": ["llm"]},
                {"name": "Analyze", "capabilities": ["reasoning"]},
                {"name": "Synthesize", "capabilities": ["generation"]}
            ]
        })

        print(f"Workflow result: {json.dumps(workflow_result, indent=2)}")

        # Get status
        status = orchestrator.get_status()
        print(f"Status: {json.dumps(status, indent=2)}")

    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    asyncio.run(example_usage())
