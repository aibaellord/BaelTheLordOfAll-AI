#!/usr/bin/env python3
"""
BAEL - Agent Execution Backend
Manages agent spawning, task delegation, and parallel execution.

This is the orchestration layer that actually runs agents with real LLM calls,
manages their lifecycles, and coordinates multi-agent collaboration.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Agent.Execution")


# =============================================================================
# ENUMS
# =============================================================================

class AgentStatus(Enum):
    """Agent lifecycle status."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class DelegationStrategy(Enum):
    """How to delegate tasks to agents."""
    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    SPECIALIZED = "specialized"
    RANDOM = "random"
    AFFINITY = "affinity"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    description: str
    tools: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class AgentPersona:
    """Personality and behavior configuration for an agent."""
    name: str
    role: str
    description: str
    system_prompt: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent: Optional[str] = None
    parent_task: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AgentState:
    """Runtime state of an agent."""
    id: str
    persona: AgentPersona
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    task_history: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    total_tasks: int = 0
    successful_tasks: int = 0


@dataclass
class ExecutionResult:
    """Result of agent execution."""
    task_id: str
    agent_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    tokens_used: int = 0
    tool_calls: List[Dict] = field(default_factory=list)


# =============================================================================
# AGENT POOL
# =============================================================================

class AgentPool:
    """
    Manages a pool of agents for parallel task execution.
    Handles spawning, lifecycle, and resource management.
    """

    def __init__(
        self,
        max_agents: int = 10,
        llm_executor: Optional[Any] = None
    ):
        self.max_agents = max_agents
        self.llm_executor = llm_executor
        self.agents: Dict[str, AgentState] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running = False
        self._worker_tasks: List[asyncio.Task] = []

    async def spawn_agent(self, persona: AgentPersona) -> AgentState:
        """Spawn a new agent with the given persona."""
        if len(self.agents) >= self.max_agents:
            # Find idle agent to reuse
            for agent in self.agents.values():
                if agent.status == AgentStatus.IDLE:
                    agent.persona = persona
                    agent.messages = []
                    agent.memory = {}
                    return agent
            raise RuntimeError("Agent pool exhausted")

        agent = AgentState(
            id=str(uuid.uuid4()),
            persona=persona
        )
        self.agents[agent.id] = agent
        logger.info(f"Spawned agent: {persona.name} ({agent.id})")
        return agent

    async def despawn_agent(self, agent_id: str) -> None:
        """Remove an agent from the pool."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            if agent.status == AgentStatus.EXECUTING:
                logger.warning(f"Despawning busy agent: {agent_id}")
            del self.agents[agent_id]
            logger.info(f"Despawned agent: {agent_id}")

    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_idle_agents(self) -> List[AgentState]:
        """Get all idle agents."""
        return [a for a in self.agents.values() if a.status == AgentStatus.IDLE]

    def get_agent_for_task(
        self,
        task: Task,
        strategy: DelegationStrategy = DelegationStrategy.LEAST_BUSY
    ) -> Optional[AgentState]:
        """Find the best agent for a task."""
        idle_agents = self.get_idle_agents()

        if not idle_agents:
            return None

        if strategy == DelegationStrategy.SPECIALIZED:
            # Find agent with matching capabilities
            for agent in idle_agents:
                agent_caps = {c.name for c in agent.persona.capabilities}
                if all(req in agent_caps for req in task.required_capabilities):
                    return agent
            # Fall back to any idle agent
            return idle_agents[0] if idle_agents else None

        elif strategy == DelegationStrategy.LEAST_BUSY:
            # Find agent with fewest completed tasks (for load balancing)
            return min(idle_agents, key=lambda a: a.total_tasks)

        elif strategy == DelegationStrategy.ROUND_ROBIN:
            # Simple round-robin
            return idle_agents[0]

        else:
            import random
            return random.choice(idle_agents) if idle_agents else None


# =============================================================================
# AGENT EXECUTOR
# =============================================================================

class AgentExecutor:
    """
    Executes tasks using agents with real LLM calls.
    Manages conversation state, tool execution, and result handling.
    """

    def __init__(
        self,
        llm_executor: Optional[Any] = None,
        tool_registry: Optional[Dict[str, Callable]] = None
    ):
        self.llm_executor = llm_executor
        self.tools = tool_registry or {}
        self.max_iterations = 10

    def register_tool(self, name: str, handler: Callable, description: str = "") -> None:
        """Register a tool for agents to use."""
        self.tools[name] = {
            "handler": handler,
            "description": description
        }

    async def execute(
        self,
        agent: AgentState,
        task: Task,
        stream_callback: Optional[Callable] = None
    ) -> ExecutionResult:
        """Execute a task with an agent."""
        start_time = time.time()
        agent.status = AgentStatus.THINKING
        agent.current_task = task.id
        task.status = AgentStatus.EXECUTING
        task.started_at = datetime.now()

        tool_calls = []
        tokens_used = 0

        try:
            # Build messages
            messages = [
                {"role": "system", "content": agent.persona.system_prompt},
                {"role": "user", "content": self._build_task_prompt(task)}
            ]

            # Add conversation history
            messages.extend(agent.messages[-20:])  # Last 20 messages

            # Agentic loop
            for iteration in range(self.max_iterations):
                agent.status = AgentStatus.THINKING

                # Call LLM
                if self.llm_executor:
                    response = await self.llm_executor.execute(
                        messages=messages,
                        temperature=agent.persona.temperature,
                        max_tokens=agent.persona.max_tokens,
                        tools=self._get_tool_definitions(),
                        stream_callback=stream_callback
                    )
                else:
                    # Mock response for testing
                    response = {
                        "content": f"Task '{task.description}' completed successfully.",
                        "tool_calls": [],
                        "tokens": 100
                    }

                tokens_used += response.get("tokens", 0)

                # Check for tool calls
                if response.get("tool_calls"):
                    agent.status = AgentStatus.EXECUTING

                    for tool_call in response["tool_calls"]:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("arguments", {})

                        tool_result = await self._execute_tool(tool_name, tool_args)
                        tool_calls.append({
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": tool_result
                        })

                        # Add tool result to messages
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "content": json.dumps(tool_result)
                        })
                else:
                    # No tool calls - task complete
                    content = response.get("content", "")

                    # Update agent state
                    agent.messages.append({"role": "assistant", "content": content})
                    agent.status = AgentStatus.COMPLETED
                    agent.current_task = None
                    agent.task_history.append(task.id)
                    agent.total_tasks += 1
                    agent.successful_tasks += 1
                    agent.last_active = datetime.now()

                    # Update task
                    task.status = AgentStatus.COMPLETED
                    task.result = content
                    task.completed_at = datetime.now()

                    return ExecutionResult(
                        task_id=task.id,
                        agent_id=agent.id,
                        success=True,
                        output=content,
                        duration_ms=(time.time() - start_time) * 1000,
                        tokens_used=tokens_used,
                        tool_calls=tool_calls
                    )

            # Max iterations reached
            raise RuntimeError("Max iterations reached")

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")

            agent.status = AgentStatus.FAILED
            agent.current_task = None
            agent.total_tasks += 1
            agent.last_active = datetime.now()

            task.status = AgentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()

            return ExecutionResult(
                task_id=task.id,
                agent_id=agent.id,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                tokens_used=tokens_used,
                tool_calls=tool_calls
            )

    def _build_task_prompt(self, task: Task) -> str:
        """Build the prompt for a task."""
        prompt = f"# Task\n{task.description}\n"

        if task.context:
            prompt += "\n## Context\n"
            for key, value in task.context.items():
                prompt += f"- {key}: {value}\n"

        if task.required_capabilities:
            prompt += f"\n## Required Capabilities\n"
            prompt += ", ".join(task.required_capabilities)

        return prompt

    def _get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": info.get("description", f"Execute {name}"),
                    "parameters": {"type": "object", "properties": {}}
                }
            }
            for name, info in self.tools.items()
        ]

    async def _execute_tool(self, name: str, arguments: Dict) -> Any:
        """Execute a tool."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}

        handler = self.tools[name]["handler"]

        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(**arguments)
            else:
                return handler(**arguments)
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# TASK DELEGATOR
# =============================================================================

class TaskDelegator:
    """
    Manages task delegation and orchestration.
    Handles task decomposition, assignment, and result aggregation.
    """

    def __init__(
        self,
        agent_pool: AgentPool,
        agent_executor: AgentExecutor,
        llm_executor: Optional[Any] = None
    ):
        self.pool = agent_pool
        self.executor = agent_executor
        self.llm_executor = llm_executor
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    async def submit_task(
        self,
        description: str,
        context: Optional[Dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        required_capabilities: Optional[List[str]] = None,
        decompose: bool = True
    ) -> Task:
        """Submit a new task for execution."""
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            priority=priority,
            context=context or {},
            required_capabilities=required_capabilities or []
        )

        self.tasks[task.id] = task

        # Optionally decompose into subtasks
        if decompose and self.llm_executor:
            subtasks = await self._decompose_task(task)
            task.subtasks = [st.id for st in subtasks]

            # Queue subtasks
            for subtask in subtasks:
                await self.pending_queue.put((subtask.priority.value, subtask))
        else:
            await self.pending_queue.put((task.priority.value, task))

        return task

    async def _decompose_task(self, task: Task) -> List[Task]:
        """Decompose a complex task into subtasks using LLM."""
        if not self.llm_executor:
            return [task]

        prompt = f"""Analyze this task and break it down into smaller, actionable subtasks.
Return a JSON array of subtask descriptions.

Task: {task.description}

Context: {json.dumps(task.context)}

Return format:
[
  {{"description": "subtask 1", "capabilities": ["cap1"]}},
  {{"description": "subtask 2", "capabilities": ["cap2"]}}
]

If the task is already simple enough, return an empty array []."""

        try:
            response = await self.llm_executor.execute(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            content = response.get("content", "[]")

            # Parse subtasks
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                subtask_data = json.loads(match.group())

                subtasks = []
                for st in subtask_data:
                    subtask = Task(
                        id=str(uuid.uuid4()),
                        description=st.get("description", ""),
                        priority=task.priority,
                        parent_task=task.id,
                        context=task.context,
                        required_capabilities=st.get("capabilities", [])
                    )
                    self.tasks[subtask.id] = subtask
                    subtasks.append(subtask)

                return subtasks if subtasks else [task]

        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")

        return [task]

    async def execute_task(self, task: Task) -> ExecutionResult:
        """Execute a single task."""
        # Find suitable agent
        agent = self.pool.get_agent_for_task(task, DelegationStrategy.SPECIALIZED)

        if not agent:
            # Spawn new agent with default persona
            from .personas import get_default_persona
            persona = get_default_persona()
            agent = await self.pool.spawn_agent(persona)

        task.assigned_agent = agent.id

        # Execute
        return await self.executor.execute(agent, task)

    async def execute_parallel(
        self,
        tasks: List[Task],
        max_parallel: int = 5
    ) -> List[ExecutionResult]:
        """Execute multiple tasks in parallel."""
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_with_limit(task: Task) -> ExecutionResult:
            async with semaphore:
                return await self.execute_task(task)

        results = await asyncio.gather(
            *[execute_with_limit(task) for task in tasks],
            return_exceptions=True
        )

        return [
            r if isinstance(r, ExecutionResult) else ExecutionResult(
                task_id="unknown",
                agent_id="unknown",
                success=False,
                error=str(r)
            )
            for r in results
        ]

    async def start(self) -> None:
        """Start the task processing loop."""
        self.running = True

        while self.running:
            try:
                # Get next task
                priority, task = await asyncio.wait_for(
                    self.pending_queue.get(),
                    timeout=1.0
                )

                # Execute
                result = await self.execute_task(task)

                # Check if parent task is complete
                if task.parent_task:
                    parent = self.tasks.get(task.parent_task)
                    if parent:
                        await self._check_parent_completion(parent)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task processing error: {e}")

    async def _check_parent_completion(self, parent: Task) -> None:
        """Check if all subtasks are complete."""
        all_complete = all(
            self.tasks.get(st_id, Task(id="")).status == AgentStatus.COMPLETED
            for st_id in parent.subtasks
        )

        if all_complete:
            # Aggregate results
            results = [
                self.tasks.get(st_id).result
                for st_id in parent.subtasks
                if self.tasks.get(st_id)
            ]

            parent.status = AgentStatus.COMPLETED
            parent.result = results
            parent.completed_at = datetime.now()

    def stop(self) -> None:
        """Stop the task processing loop."""
        self.running = False


# =============================================================================
# PERSONAS
# =============================================================================

def get_default_persona() -> AgentPersona:
    """Get the default agent persona."""
    return AgentPersona(
        name="Assistant",
        role="General Assistant",
        description="A helpful AI assistant that can handle various tasks.",
        system_prompt="""You are a helpful AI assistant. You can:
- Answer questions accurately
- Execute tasks step by step
- Use tools when needed
- Ask for clarification when unsure

Be concise, accurate, and helpful.""",
        capabilities=[
            AgentCapability(
                name="general",
                description="General knowledge and reasoning",
                domains=["general", "analysis", "writing"]
            )
        ]
    )


def get_coding_persona() -> AgentPersona:
    """Get a coding-focused persona."""
    return AgentPersona(
        name="Developer",
        role="Software Developer",
        description="Expert programmer who writes clean, efficient code.",
        system_prompt="""You are an expert software developer. You:
- Write clean, well-documented code
- Follow best practices and design patterns
- Handle errors gracefully
- Explain your implementation decisions

Focus on practical, working solutions.""",
        capabilities=[
            AgentCapability(
                name="coding",
                description="Software development",
                tools=["read_file", "write_file", "run_code", "search_code"],
                domains=["python", "javascript", "typescript", "rust", "go"]
            )
        ],
        temperature=0.3
    )


def get_researcher_persona() -> AgentPersona:
    """Get a research-focused persona."""
    return AgentPersona(
        name="Researcher",
        role="Research Analyst",
        description="Thorough researcher who finds and synthesizes information.",
        system_prompt="""You are a research analyst. You:
- Search thoroughly for relevant information
- Cross-reference multiple sources
- Synthesize findings clearly
- Cite sources appropriately

Be comprehensive but focused.""",
        capabilities=[
            AgentCapability(
                name="research",
                description="Information research and synthesis",
                tools=["web_search", "read_file", "summarize"],
                domains=["research", "analysis", "synthesis"]
            )
        ],
        temperature=0.5
    )


# =============================================================================
# AGENT BACKEND - MAIN INTERFACE
# =============================================================================

class AgentBackend:
    """
    Main interface for the agent execution system.
    Coordinates pool, executor, and delegator.
    """

    def __init__(
        self,
        llm_executor: Optional[Any] = None,
        max_agents: int = 10
    ):
        self.llm_executor = llm_executor
        self.pool = AgentPool(max_agents=max_agents, llm_executor=llm_executor)
        self.executor = AgentExecutor(llm_executor=llm_executor)
        self.delegator = TaskDelegator(
            agent_pool=self.pool,
            agent_executor=self.executor,
            llm_executor=llm_executor
        )
        self._running = False
        self._background_task: Optional[asyncio.Task] = None

    def register_tool(self, name: str, handler: Callable, description: str = "") -> None:
        """Register a tool for agents to use."""
        self.executor.register_tool(name, handler, description)

    async def spawn_agent(self, persona: Optional[AgentPersona] = None) -> AgentState:
        """Spawn a new agent."""
        persona = persona or get_default_persona()
        return await self.pool.spawn_agent(persona)

    async def execute_task(
        self,
        description: str,
        context: Optional[Dict] = None,
        persona: Optional[AgentPersona] = None,
        decompose: bool = False
    ) -> ExecutionResult:
        """Execute a task directly."""
        task = Task(
            id=str(uuid.uuid4()),
            description=description,
            context=context or {}
        )

        agent = await self.spawn_agent(persona)
        return await self.executor.execute(agent, task)

    async def submit_task(
        self,
        description: str,
        context: Optional[Dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        decompose: bool = True
    ) -> Task:
        """Submit a task for async execution."""
        return await self.delegator.submit_task(
            description=description,
            context=context,
            priority=priority,
            decompose=decompose
        )

    async def execute_parallel(
        self,
        descriptions: List[str],
        max_parallel: int = 5
    ) -> List[ExecutionResult]:
        """Execute multiple tasks in parallel."""
        tasks = [
            Task(id=str(uuid.uuid4()), description=desc)
            for desc in descriptions
        ]
        return await self.delegator.execute_parallel(tasks, max_parallel)

    async def start(self) -> None:
        """Start the background task processing."""
        if self._running:
            return

        self._running = True
        self._background_task = asyncio.create_task(self.delegator.start())
        logger.info("Agent backend started")

    async def stop(self) -> None:
        """Stop the background task processing."""
        self._running = False
        self.delegator.stop()

        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent backend stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get backend status."""
        return {
            "running": self._running,
            "total_agents": len(self.pool.agents),
            "idle_agents": len(self.pool.get_idle_agents()),
            "pending_tasks": self.delegator.pending_queue.qsize(),
            "total_tasks": len(self.delegator.tasks)
        }


# =============================================================================
# SINGLETON
# =============================================================================

_backend: Optional[AgentBackend] = None


def get_agent_backend(llm_executor: Optional[Any] = None) -> AgentBackend:
    """Get the global agent backend instance."""
    global _backend
    if _backend is None:
        _backend = AgentBackend(llm_executor=llm_executor)
    return _backend


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def demo():
        backend = get_agent_backend()

        # Execute a simple task
        result = await backend.execute_task(
            description="What is 2 + 2?",
            persona=get_default_persona()
        )

        print(f"Result: {result.output}")
        print(f"Success: {result.success}")
        print(f"Duration: {result.duration_ms:.2f}ms")

    asyncio.run(demo())
