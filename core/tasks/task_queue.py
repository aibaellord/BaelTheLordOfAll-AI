#!/usr/bin/env python3
"""
BAEL - Background Task Queue
Manages long-running tasks that execute asynchronously.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.TaskQueue")


# =============================================================================
# ENUMS
# =============================================================================

class TaskStatus(Enum):
    """Task lifecycle status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TaskDefinition:
    """Definition of a background task."""
    name: str
    handler: Callable
    description: str = ""
    max_retries: int = 3
    timeout_seconds: float = 300
    priority: TaskPriority = TaskPriority.NORMAL


@dataclass
class QueuedTask:
    """A task instance in the queue."""
    id: str
    task_name: str
    arguments: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0
    progress_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "arguments": self.arguments,
            "priority": self.priority.name,
            "status": self.status.value,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "retries": self.retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "progress_message": self.progress_message
        }


@dataclass
class TaskProgress:
    """Progress update for a task."""
    task_id: str
    progress: float  # 0-100
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TASK QUEUE
# =============================================================================

class BackgroundTaskQueue:
    """
    Manages background task execution with priorities, retries, and progress tracking.
    """

    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 1000
    ):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size

        # Task registry
        self.task_definitions: Dict[str, TaskDefinition] = {}

        # Queue storage
        self.pending: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.tasks: Dict[str, QueuedTask] = {}
        self.running: Set[str] = set()

        # Workers
        self._workers: List[asyncio.Task] = []
        self._running = False

        # Callbacks
        self._progress_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []

    def register_task(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        max_retries: int = 3,
        timeout_seconds: float = 300,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> None:
        """Register a task type."""
        self.task_definitions[name] = TaskDefinition(
            name=name,
            handler=handler,
            description=description,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            priority=priority
        )
        logger.info(f"Registered task: {name}")

    async def enqueue(
        self,
        task_name: str,
        arguments: Optional[Dict] = None,
        priority: Optional[TaskPriority] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a task to the queue."""
        if task_name not in self.task_definitions:
            raise ValueError(f"Unknown task: {task_name}")

        definition = self.task_definitions[task_name]

        task = QueuedTask(
            id=str(uuid.uuid4()),
            task_name=task_name,
            arguments=arguments or {},
            priority=priority or definition.priority,
            metadata=metadata or {}
        )

        self.tasks[task.id] = task

        # Add to priority queue (lower number = higher priority)
        await self.pending.put((task.priority.value, task.id))

        logger.info(f"Enqueued task: {task_name} ({task.id})")
        return task.id

    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True

        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"Started {self.max_workers} task queue workers")

    async def stop(self) -> None:
        """Stop the task queue."""
        self._running = False

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("Task queue stopped")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks."""
        while self._running:
            try:
                # Get next task
                priority, task_id = await asyncio.wait_for(
                    self.pending.get(),
                    timeout=1.0
                )

                if task_id not in self.tasks:
                    continue

                task = self.tasks[task_id]

                if task.status == TaskStatus.CANCELLED:
                    continue

                await self._execute_task(task, worker_id)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def _execute_task(self, task: QueuedTask, worker_id: int) -> None:
        """Execute a single task."""
        if task.task_name not in self.task_definitions:
            task.status = TaskStatus.FAILED
            task.error = f"Task definition not found: {task.task_name}"
            return

        definition = self.task_definitions[task.task_name]

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running.add(task.id)

        logger.info(f"Worker {worker_id} executing: {task.task_name} ({task.id})")

        try:
            # Create progress callback
            async def update_progress(progress: float, message: str = "") -> None:
                task.progress = progress
                task.progress_message = message
                await self._notify_progress(task)

            # Execute with timeout
            if asyncio.iscoroutinefunction(definition.handler):
                result = await asyncio.wait_for(
                    definition.handler(
                        **task.arguments,
                        progress_callback=update_progress
                    ),
                    timeout=definition.timeout_seconds
                )
            else:
                result = definition.handler(**task.arguments)

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.progress = 100
            task.completed_at = datetime.now()

            logger.info(f"Task completed: {task.id}")
            await self._notify_completion(task)

        except asyncio.TimeoutError:
            task.error = "Task timed out"
            await self._handle_failure(task, definition)

        except Exception as e:
            task.error = str(e)
            await self._handle_failure(task, definition)

        finally:
            self.running.discard(task.id)

    async def _handle_failure(self, task: QueuedTask, definition: TaskDefinition) -> None:
        """Handle task failure with retry logic."""
        task.retries += 1

        if task.retries <= definition.max_retries:
            task.status = TaskStatus.RETRYING
            logger.warning(f"Retrying task {task.id} (attempt {task.retries})")

            # Re-queue with delay
            await asyncio.sleep(2 ** task.retries)  # Exponential backoff
            await self.pending.put((task.priority.value, task.id))
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            logger.error(f"Task failed permanently: {task.id} - {task.error}")
            await self._notify_completion(task)

    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        self.running.discard(task_id)

        logger.info(f"Cancelled task: {task_id}")
        return True

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_status(self) -> Dict[str, Any]:
        """Get queue status."""
        by_status = {}
        for task in self.tasks.values():
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "running": self._running,
            "workers": self.max_workers,
            "pending_count": self.pending.qsize(),
            "running_count": len(self.running),
            "total_tasks": len(self.tasks),
            "by_status": by_status
        }

    def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50
    ) -> List[QueuedTask]:
        """Get tasks with optional filtering."""
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks[:limit]

    def on_progress(self, callback: Callable) -> None:
        """Register a progress callback."""
        self._progress_callbacks.append(callback)

    def on_completion(self, callback: Callable) -> None:
        """Register a completion callback."""
        self._completion_callbacks.append(callback)

    async def _notify_progress(self, task: QueuedTask) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    async def _notify_completion(self, task: QueuedTask) -> None:
        """Notify completion callbacks."""
        for callback in self._completion_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")


# =============================================================================
# BUILT-IN TASKS
# =============================================================================

async def cleanup_task(
    older_than_hours: int = 24,
    progress_callback: Optional[Callable] = None
) -> Dict[str, int]:
    """Clean up old data."""
    if progress_callback:
        await progress_callback(10, "Starting cleanup...")

    await asyncio.sleep(1)

    if progress_callback:
        await progress_callback(50, "Cleaning old memories...")

    await asyncio.sleep(1)

    if progress_callback:
        await progress_callback(90, "Finalizing...")

    return {"cleaned_items": 42}


async def index_rebuild_task(
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Rebuild search indices."""
    if progress_callback:
        await progress_callback(0, "Starting index rebuild...")

    for i in range(1, 11):
        await asyncio.sleep(0.5)
        if progress_callback:
            await progress_callback(i * 10, f"Indexing batch {i}/10...")

    return {"indexed_documents": 1000}


async def model_update_check_task(
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Check for model updates."""
    if progress_callback:
        await progress_callback(50, "Checking for updates...")

    await asyncio.sleep(2)

    return {
        "updates_available": True,
        "models": [
            {"name": "claude-3.5-sonnet", "current": True},
            {"name": "claude-4", "available": True}
        ]
    }


# =============================================================================
# SINGLETON
# =============================================================================

_queue: Optional[BackgroundTaskQueue] = None


def get_task_queue() -> BackgroundTaskQueue:
    """Get the global task queue instance."""
    global _queue

    if _queue is None:
        _queue = BackgroundTaskQueue()

        # Register built-in tasks
        _queue.register_task(
            "cleanup",
            cleanup_task,
            "Clean up old data",
            priority=TaskPriority.LOW
        )
        _queue.register_task(
            "index_rebuild",
            index_rebuild_task,
            "Rebuild search indices",
            priority=TaskPriority.NORMAL
        )
        _queue.register_task(
            "model_update_check",
            model_update_check_task,
            "Check for model updates",
            priority=TaskPriority.BACKGROUND
        )

    return _queue


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def demo():
        queue = get_task_queue()

        # Start the queue
        await queue.start()

        # Enqueue some tasks
        task_id = await queue.enqueue("cleanup", {"older_than_hours": 12})
        print(f"Enqueued task: {task_id}")

        # Wait for completion
        await asyncio.sleep(5)

        task = queue.get_task(task_id)
        print(f"Task status: {task.status.value}")
        print(f"Result: {task.result}")

        # Get status
        status = queue.get_status()
        print(f"Queue status: {status}")

        await queue.stop()

    asyncio.run(demo())
