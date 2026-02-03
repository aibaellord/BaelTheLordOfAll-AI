#!/usr/bin/env python3
"""
BAEL - Agent Execution Engine
Real agent execution with task delegation, parallel processing, and result aggregation.

This is the engine that makes agents actually DO things, not just plan.
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.Agents.Engine")


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
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


class AgentCapability(Enum):
    """Agent capabilities."""
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    API_CALLS = "api_calls"
    DATA_ANALYSIS = "data_analysis"
    REASONING = "reasoning"
    CREATIVE = "creative"
    RESEARCH = "research"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str = ""
    name: str = ""
    description: str = ""
    action: str = ""  # The action to perform
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    result: Optional[TaskResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: float = 300.0

    def __post_init__(self):
        if not self.id:
            self.id = f"task-{uuid.uuid4().hex[:8]}"


@dataclass
class AgentState:
    """State of an agent."""
    id: str
    name: str
    capabilities: List[AgentCapability]
    status: str = "idle"  # idle, busy, offline
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionPlan:
    """A plan for executing multiple tasks."""
    id: str = ""
    name: str = ""
    tasks: List[Task] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)  # Groups of task IDs that can run in parallel
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = f"plan-{uuid.uuid4().hex[:8]}"


# =============================================================================
# ACTION HANDLERS
# =============================================================================

class ActionHandler(ABC):
    """Base class for action handlers."""

    @property
    @abstractmethod
    def action_name(self) -> str:
        """Get the action name this handler handles."""
        pass

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        """Execute the action with given parameters."""
        pass


class CodeExecutionHandler(ActionHandler):
    """Handler for code execution actions."""

    @property
    def action_name(self) -> str:
        return "execute_code"

    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        code = parameters.get("code", "")
        language = parameters.get("language", "python")
        task_id = parameters.get("_task_id", "unknown")

        start = time.time()

        if language == "python":
            try:
                # Safe execution with restricted builtins
                safe_builtins = {
                    'print': print, 'len': len, 'range': range,
                    'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                    'sum': sum, 'min': min, 'max': max, 'abs': abs,
                    'sorted': sorted, 'enumerate': enumerate, 'zip': zip,
                    'map': map, 'filter': filter, 'isinstance': isinstance,
                    'True': True, 'False': False, 'None': None,
                }
                local_scope: Dict[str, Any] = {}
                exec(code, {"__builtins__": safe_builtins}, local_scope)

                output = local_scope.get('result', local_scope.get('output', 'Executed successfully'))
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    output=output,
                    duration_ms=(time.time() - start) * 1000
                )
            except Exception as e:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    output=None,
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000
                )
        else:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error=f"Language {language} not supported",
                duration_ms=(time.time() - start) * 1000
            )


class LLMCallHandler(ActionHandler):
    """Handler for LLM API calls."""

    def __init__(self):
        self._executor = None

    async def _get_executor(self):
        if not self._executor:
            try:
                from core.wiring import LLMExecutor
                self._executor = LLMExecutor()
            except ImportError:
                pass
        return self._executor

    @property
    def action_name(self) -> str:
        return "llm_call"

    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        prompt = parameters.get("prompt", "")
        system_prompt = parameters.get("system_prompt")
        task_id = parameters.get("_task_id", "unknown")

        start = time.time()
        executor = await self._get_executor()

        if not executor:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error="LLM executor not available",
                duration_ms=(time.time() - start) * 1000
            )

        try:
            result = await executor.execute(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=parameters.get("temperature", 0.7),
                max_tokens=parameters.get("max_tokens", 2048)
            )
            return TaskResult(
                task_id=task_id,
                success=True,
                output=result.get("content", ""),
                duration_ms=(time.time() - start) * 1000,
                metadata={"model": result.get("model"), "tokens": result.get("tokens_used")}
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )


class FileOperationHandler(ActionHandler):
    """Handler for file operations."""

    @property
    def action_name(self) -> str:
        return "file_operation"

    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        operation = parameters.get("operation", "read")
        path = parameters.get("path", "")
        task_id = parameters.get("_task_id", "unknown")

        start = time.time()

        try:
            if operation == "read":
                with open(path, 'r') as f:
                    content = f.read()
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    output=content,
                    duration_ms=(time.time() - start) * 1000
                )
            elif operation == "write":
                content = parameters.get("content", "")
                with open(path, 'w') as f:
                    f.write(content)
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    output=f"Written {len(content)} bytes to {path}",
                    duration_ms=(time.time() - start) * 1000
                )
            elif operation == "list":
                import os
                files = os.listdir(path)
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    output=files,
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    output=None,
                    error=f"Unknown operation: {operation}",
                    duration_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )


class WebSearchHandler(ActionHandler):
    """Handler for web search actions."""

    @property
    def action_name(self) -> str:
        return "web_search"

    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        import os
        query = parameters.get("query", "")
        task_id = parameters.get("_task_id", "unknown")

        start = time.time()

        # Try Brave Search API
        api_key = os.environ.get("BRAVE_API_KEY")
        if api_key:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": api_key},
                        params={"q": query, "count": 5}
                    ) as resp:
                        data = await resp.json()
                        results = [
                            {"title": r.get("title"), "url": r.get("url"), "description": r.get("description")}
                            for r in data.get("web", {}).get("results", [])
                        ]
                        return TaskResult(
                            task_id=task_id,
                            success=True,
                            output=results,
                            duration_ms=(time.time() - start) * 1000
                        )
            except Exception as e:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    output=None,
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000
                )

        return TaskResult(
            task_id=task_id,
            success=False,
            output=None,
            error="No search API available (set BRAVE_API_KEY)",
            duration_ms=(time.time() - start) * 1000
        )


class ToolCallHandler(ActionHandler):
    """Handler for calling registered tools."""

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None):
        self.tool_registry = tool_registry or {}

    @property
    def action_name(self) -> str:
        return "tool_call"

    async def execute(self, parameters: Dict[str, Any]) -> TaskResult:
        tool_name = parameters.get("tool_name", "")
        tool_params = parameters.get("tool_params", {})
        task_id = parameters.get("_task_id", "unknown")

        start = time.time()

        if tool_name not in self.tool_registry:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error=f"Tool not found: {tool_name}",
                duration_ms=(time.time() - start) * 1000
            )

        try:
            tool = self.tool_registry[tool_name]
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**tool_params)
            else:
                result = tool.execute(**tool_params)

            return TaskResult(
                task_id=task_id,
                success=True,
                output=result,
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )


# =============================================================================
# TASK PLANNER
# =============================================================================

class TaskPlanner:
    """Plans task execution order based on dependencies."""

    def __init__(self, llm_executor: Optional[Any] = None):
        self._llm = llm_executor

    async def decompose_goal(self, goal: str, context: Optional[Dict] = None) -> List[Task]:
        """Decompose a high-level goal into executable tasks."""
        if self._llm:
            prompt = f"""Decompose this goal into specific executable tasks:

Goal: {goal}

{f"Context: {json.dumps(context)}" if context else ""}

Return a JSON array of tasks, each with:
- name: Short task name
- description: What to do
- action: One of [execute_code, llm_call, file_operation, web_search, tool_call]
- parameters: Dict of parameters for the action
- dependencies: Array of task names this depends on (empty if none)

Example:
[
  {{"name": "research", "description": "Search for info", "action": "web_search", "parameters": {{"query": "..."}}, "dependencies": []}},
  {{"name": "analyze", "description": "Analyze results", "action": "llm_call", "parameters": {{"prompt": "..."}}, "dependencies": ["research"]}}
]

Return ONLY the JSON array, no other text."""

            try:
                result = await self._llm.execute(prompt=prompt, temperature=0.3)
                content = result.get("content", "[]")
                # Extract JSON from response
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                tasks_data = json.loads(content.strip())

                tasks = []
                task_name_to_id = {}

                for td in tasks_data:
                    task = Task(
                        name=td.get("name", "Unnamed"),
                        description=td.get("description", ""),
                        action=td.get("action", "llm_call"),
                        parameters=td.get("parameters", {})
                    )
                    tasks.append(task)
                    task_name_to_id[task.name] = task.id

                # Resolve dependencies
                for i, td in enumerate(tasks_data):
                    dep_names = td.get("dependencies", [])
                    tasks[i].dependencies = [
                        task_name_to_id.get(name, "")
                        for name in dep_names
                        if name in task_name_to_id
                    ]

                return tasks

            except Exception as e:
                logger.error(f"Failed to decompose goal: {e}")

        # Fallback: single LLM task
        return [Task(
            name="execute_goal",
            description=goal,
            action="llm_call",
            parameters={"prompt": goal}
        )]

    def create_execution_plan(self, tasks: List[Task]) -> ExecutionPlan:
        """Create an execution plan with parallel groups."""
        plan = ExecutionPlan(name="Auto-generated plan", tasks=tasks)

        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        completed: Set[str] = set()
        remaining = set(t.id for t in tasks)

        while remaining:
            # Find tasks with all dependencies satisfied
            ready = [
                tid for tid in remaining
                if all(dep in completed for dep in task_map[tid].dependencies)
            ]

            if not ready:
                # Circular dependency or invalid state
                logger.warning("Could not resolve all dependencies")
                ready = list(remaining)[:1]  # Force progress

            plan.parallel_groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return plan


# =============================================================================
# AGENT EXECUTION ENGINE
# =============================================================================

class AgentExecutionEngine:
    """
    The core engine that executes agent tasks.
    Manages task queue, parallel execution, retries, and result aggregation.
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        tool_registry: Optional[Dict[str, Any]] = None
    ):
        self.max_concurrent = max_concurrent
        self.tool_registry = tool_registry or {}

        # Action handlers
        self.handlers: Dict[str, ActionHandler] = {}
        self._register_default_handlers()

        # Task management
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}

        # Agents
        self.agents: Dict[str, AgentState] = {}

        # Planner
        self.planner = TaskPlanner()

        # Control
        self._running = False
        self._workers: List[asyncio.Task] = []

        # Callbacks
        self.on_task_start: Optional[Callable[[Task], None]] = None
        self.on_task_complete: Optional[Callable[[Task, TaskResult], None]] = None
        self.on_task_failed: Optional[Callable[[Task, str], None]] = None

    def _register_default_handlers(self):
        """Register default action handlers."""
        handlers = [
            CodeExecutionHandler(),
            LLMCallHandler(),
            FileOperationHandler(),
            WebSearchHandler(),
            ToolCallHandler(self.tool_registry),
        ]
        for handler in handlers:
            self.handlers[handler.action_name] = handler

    def register_handler(self, handler: ActionHandler):
        """Register a custom action handler."""
        self.handlers[handler.action_name] = handler

    async def start(self):
        """Start the execution engine."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting agent execution engine with {self.max_concurrent} workers")

        # Start worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)

    async def stop(self):
        """Stop the execution engine."""
        self._running = False

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Agent execution engine stopped")

    async def _worker(self, worker_id: str):
        """Worker that processes tasks from the queue."""
        while self._running:
            try:
                # Get task from queue (with timeout to allow shutdown)
                try:
                    priority, task_id = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                task = self.active_tasks.get(task_id)
                if not task or task.status == TaskStatus.CANCELLED:
                    continue

                # Check dependencies
                deps_satisfied = all(
                    dep_id in self.completed_tasks and
                    self.completed_tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )

                if not deps_satisfied:
                    # Re-queue with lower priority
                    await self.task_queue.put((priority + 1, task_id))
                    await asyncio.sleep(0.1)
                    continue

                # Execute task
                logger.info(f"[{worker_id}] Executing task: {task.name}")
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()

                if self.on_task_start:
                    self.on_task_start(task)

                try:
                    result = await self._execute_task(task)
                    task.result = result
                    task.completed_at = datetime.now()

                    if result.success:
                        task.status = TaskStatus.COMPLETED
                        if self.on_task_complete:
                            self.on_task_complete(task, result)
                    else:
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            task.status = TaskStatus.PENDING
                            await self.task_queue.put((priority, task_id))
                            logger.warning(f"Task {task.name} failed, retrying ({task.retry_count}/{task.max_retries})")
                        else:
                            task.status = TaskStatus.FAILED
                            if self.on_task_failed:
                                self.on_task_failed(task, result.error or "Unknown error")

                except asyncio.TimeoutError:
                    task.status = TaskStatus.FAILED
                    task.result = TaskResult(task_id=task.id, success=False, output=None, error="Timeout")
                    if self.on_task_failed:
                        self.on_task_failed(task, "Timeout")

                except Exception as e:
                    logger.error(f"Task execution error: {e}\n{traceback.format_exc()}")
                    task.status = TaskStatus.FAILED
                    task.result = TaskResult(task_id=task.id, success=False, output=None, error=str(e))
                    if self.on_task_failed:
                        self.on_task_failed(task, str(e))

                finally:
                    # Move to completed
                    self.completed_tasks[task_id] = task
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                    self.task_results[task_id] = task.result

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute a single task."""
        handler = self.handlers.get(task.action)

        if not handler:
            return TaskResult(
                task_id=task.id,
                success=False,
                output=None,
                error=f"No handler for action: {task.action}"
            )

        # Add task ID to parameters
        params = {**task.parameters, "_task_id": task.id}

        # Execute with timeout
        return await asyncio.wait_for(
            handler.execute(params),
            timeout=task.timeout_seconds
        )

    async def submit_task(self, task: Task) -> str:
        """Submit a task for execution."""
        self.active_tasks[task.id] = task
        task.status = TaskStatus.QUEUED
        await self.task_queue.put((task.priority.value, task.id))
        logger.info(f"Submitted task: {task.name} ({task.id})")
        return task.id

    async def submit_plan(self, plan: ExecutionPlan) -> List[str]:
        """Submit an execution plan."""
        task_ids = []
        for task in plan.tasks:
            tid = await self.submit_task(task)
            task_ids.append(tid)
        return task_ids

    async def execute_goal(
        self,
        goal: str,
        context: Optional[Dict] = None,
        wait: bool = True
    ) -> Dict[str, TaskResult]:
        """
        High-level: decompose a goal into tasks and execute them.
        """
        # Decompose
        tasks = await self.planner.decompose_goal(goal, context)
        logger.info(f"Decomposed goal into {len(tasks)} tasks")

        # Create plan
        plan = self.planner.create_execution_plan(tasks)
        logger.info(f"Created plan with {len(plan.parallel_groups)} parallel groups")

        # Submit
        task_ids = await self.submit_plan(plan)

        if wait:
            # Wait for all tasks to complete
            while any(tid in self.active_tasks for tid in task_ids):
                await asyncio.sleep(0.1)

            return {tid: self.task_results.get(tid) for tid in task_ids}

        return {}

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].status
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].status
        return None

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a completed task."""
        return self.task_results.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = TaskStatus.CANCELLED
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "queued": self.task_queue.qsize(),
            "workers": len(self._workers),
            "running": self._running,
            "handlers": list(self.handlers.keys())
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engine: Optional[AgentExecutionEngine] = None


async def get_engine() -> AgentExecutionEngine:
    """Get or create the global execution engine."""
    global _engine
    if _engine is None:
        _engine = AgentExecutionEngine()
        await _engine.start()
    return _engine


async def execute(goal: str, context: Optional[Dict] = None) -> Dict[str, TaskResult]:
    """Quick execute a goal."""
    engine = await get_engine()
    return await engine.execute_goal(goal, context)


async def run_task(
    action: str,
    parameters: Dict[str, Any],
    name: str = "Quick task"
) -> TaskResult:
    """Run a single task immediately."""
    engine = await get_engine()
    task = Task(name=name, action=action, parameters=parameters)
    task_id = await engine.submit_task(task)

    # Wait for completion
    while task_id in engine.active_tasks:
        await asyncio.sleep(0.05)

    return engine.get_task_result(task_id)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "List files in the current directory"

        print(f"\n🤖 BAEL AGENT EXECUTION ENGINE")
        print(f"{'='*50}")
        print(f"Goal: {goal}\n")

        engine = AgentExecutionEngine()

        # Add callbacks
        engine.on_task_start = lambda t: print(f"▶️  Starting: {t.name}")
        engine.on_task_complete = lambda t, r: print(f"✅ Completed: {t.name} - {str(r.output)[:100]}")
        engine.on_task_failed = lambda t, e: print(f"❌ Failed: {t.name} - {e}")

        await engine.start()

        try:
            results = await engine.execute_goal(goal)

            print(f"\n{'='*50}")
            print(f"📊 RESULTS:")
            for task_id, result in results.items():
                if result:
                    status = "✓" if result.success else "✗"
                    print(f"  {status} {task_id}: {str(result.output)[:200]}")
        finally:
            await engine.stop()

    asyncio.run(main())
