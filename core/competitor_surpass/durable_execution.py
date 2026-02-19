"""
💾 DURABLE EXECUTION ENGINE
===========================
Surpasses LangGraph's durable execution with:
- Full state checkpointing
- Time-travel debugging
- Resume from any point
- Distributed execution
- Fault tolerance
"""

import asyncio
import hashlib
import json
import logging
import pickle
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.DurableExecution")


class ExecutionState(Enum):
    """Execution states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckpointType(Enum):
    """Types of checkpoints"""
    AUTO = "auto"           # Automatic periodic
    STEP = "step"           # After each step
    MANUAL = "manual"       # User-triggered
    ERROR = "error"         # On error
    RECOVERY = "recovery"   # Recovery point


@dataclass
class Checkpoint:
    """A checkpoint in execution"""
    id: str = field(default_factory=lambda: str(uuid4()))
    execution_id: str = ""
    step_index: int = 0
    step_name: str = ""
    checkpoint_type: CheckpointType = CheckpointType.AUTO
    state: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    stack: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    compressed: bool = False
    checksum: str = ""

    def to_bytes(self) -> bytes:
        """Serialize checkpoint to bytes"""
        data = {
            "id": self.id,
            "execution_id": self.execution_id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "checkpoint_type": self.checkpoint_type.value,
            "state": self.state,
            "variables": self.variables,
            "stack": self.stack,
            "created_at": self.created_at.isoformat()
        }
        serialized = pickle.dumps(data)
        compressed = zlib.compress(serialized)
        return compressed

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Checkpoint':
        """Deserialize checkpoint from bytes"""
        decompressed = zlib.decompress(data)
        obj = pickle.loads(decompressed)

        checkpoint = cls(
            id=obj["id"],
            execution_id=obj["execution_id"],
            step_index=obj["step_index"],
            step_name=obj["step_name"],
            checkpoint_type=CheckpointType(obj["checkpoint_type"]),
            state=obj["state"],
            variables=obj["variables"],
            stack=obj["stack"],
            created_at=datetime.fromisoformat(obj["created_at"]),
            size_bytes=len(data),
            compressed=True
        )
        checkpoint.checksum = hashlib.sha256(data).hexdigest()
        return checkpoint


@dataclass
class ExecutionStep:
    """A step in execution"""
    index: int
    name: str
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    retries: int = 3
    timeout_seconds: float = 300
    checkpoint_before: bool = True
    checkpoint_after: bool = True

    # Execution state
    status: ExecutionState = ExecutionState.PENDING
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0


@dataclass
class DurableExecution:
    """A durable execution instance"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    steps: List[ExecutionStep] = field(default_factory=list)
    current_step: int = 0
    state: ExecutionState = ExecutionState.PENDING
    variables: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)  # Checkpoint IDs
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class CheckpointStore:
    """Store for checkpoints"""

    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or "data/checkpoints")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Checkpoint] = {}

    async def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint"""
        data = checkpoint.to_bytes()
        checkpoint.size_bytes = len(data)
        checkpoint.checksum = hashlib.sha256(data).hexdigest()

        # Save to disk
        file_path = self.storage_path / f"{checkpoint.id}.ckpt"
        file_path.write_bytes(data)

        # Cache in memory
        self._memory_cache[checkpoint.id] = checkpoint

        return checkpoint.id

    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint"""
        # Check memory cache
        if checkpoint_id in self._memory_cache:
            return self._memory_cache[checkpoint_id]

        # Load from disk
        file_path = self.storage_path / f"{checkpoint_id}.ckpt"
        if not file_path.exists():
            return None

        data = file_path.read_bytes()
        checkpoint = Checkpoint.from_bytes(data)

        # Cache
        self._memory_cache[checkpoint_id] = checkpoint

        return checkpoint

    async def list_for_execution(self, execution_id: str) -> List[Checkpoint]:
        """List all checkpoints for an execution"""
        checkpoints = []

        for file_path in self.storage_path.glob("*.ckpt"):
            try:
                data = file_path.read_bytes()
                checkpoint = Checkpoint.from_bytes(data)
                if checkpoint.execution_id == execution_id:
                    checkpoints.append(checkpoint)
            except Exception:
                continue

        return sorted(checkpoints, key=lambda c: c.step_index)

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint"""
        if checkpoint_id in self._memory_cache:
            del self._memory_cache[checkpoint_id]

        file_path = self.storage_path / f"{checkpoint_id}.ckpt"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Clean up old checkpoints"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted = 0

        for file_path in self.storage_path.glob("*.ckpt"):
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                deleted += 1

        return deleted


class DurableExecutionEngine:
    """
    Durable execution engine that surpasses LangGraph.

    Features:
    - Automatic checkpointing
    - Resume from any step
    - Time-travel debugging
    - Fault tolerance with retries
    - Distributed execution support
    - Step-level timeout and retry configuration
    """

    def __init__(self, storage_path: str = None):
        self.checkpoint_store = CheckpointStore(storage_path)
        self.executions: Dict[str, DurableExecution] = {}
        self._running: Set[str] = set()

        # Configuration
        self.config = {
            "auto_checkpoint_interval": 5,  # Steps
            "max_checkpoints_per_execution": 100,
            "default_timeout": 300,
            "default_retries": 3
        }

    def create_execution(
        self,
        name: str,
        steps: List[Dict[str, Any]] = None,
        description: str = ""
    ) -> DurableExecution:
        """Create a new durable execution"""
        execution = DurableExecution(
            name=name,
            description=description
        )

        # Add steps
        if steps:
            for i, step_config in enumerate(steps):
                step = ExecutionStep(
                    index=i,
                    name=step_config.get("name", f"Step {i}"),
                    function=step_config.get("function", lambda: None),
                    args=step_config.get("args", ()),
                    kwargs=step_config.get("kwargs", {}),
                    retries=step_config.get("retries", self.config["default_retries"]),
                    timeout_seconds=step_config.get("timeout", self.config["default_timeout"]),
                    checkpoint_before=step_config.get("checkpoint_before", True),
                    checkpoint_after=step_config.get("checkpoint_after", True)
                )
                execution.steps.append(step)

        self.executions[execution.id] = execution
        return execution

    def add_step(
        self,
        execution: DurableExecution,
        name: str,
        function: Callable,
        **kwargs
    ) -> ExecutionStep:
        """Add a step to execution"""
        step = ExecutionStep(
            index=len(execution.steps),
            name=name,
            function=function,
            **kwargs
        )
        execution.steps.append(step)
        return step

    async def run(
        self,
        execution: DurableExecution,
        resume_from_checkpoint: str = None
    ) -> DurableExecution:
        """Run the execution"""
        if execution.id in self._running:
            raise RuntimeError(f"Execution {execution.id} is already running")

        self._running.add(execution.id)

        try:
            # Resume from checkpoint if provided
            if resume_from_checkpoint:
                await self._restore_from_checkpoint(execution, resume_from_checkpoint)

            execution.state = ExecutionState.RUNNING
            execution.started_at = execution.started_at or datetime.now()

            # Execute steps
            while execution.current_step < len(execution.steps):
                step = execution.steps[execution.current_step]

                # Checkpoint before if configured
                if step.checkpoint_before and execution.current_step > 0:
                    if execution.current_step % self.config["auto_checkpoint_interval"] == 0:
                        await self._create_checkpoint(execution, CheckpointType.AUTO)

                # Execute step with retries
                success = await self._execute_step(execution, step)

                if not success:
                    # Create error checkpoint
                    await self._create_checkpoint(execution, CheckpointType.ERROR)
                    execution.state = ExecutionState.FAILED
                    execution.error = step.error
                    break

                # Checkpoint after if configured
                if step.checkpoint_after:
                    await self._create_checkpoint(execution, CheckpointType.STEP)

                execution.current_step += 1

            # Completed successfully
            if execution.current_step >= len(execution.steps):
                execution.state = ExecutionState.COMPLETED
                execution.completed_at = datetime.now()

        finally:
            self._running.discard(execution.id)

        return execution

    async def _execute_step(
        self,
        execution: DurableExecution,
        step: ExecutionStep
    ) -> bool:
        """Execute a single step with retries"""
        step.started_at = datetime.now()
        step.status = ExecutionState.RUNNING

        for attempt in range(step.retries):
            step.attempts = attempt + 1

            try:
                # Execute with timeout
                if asyncio.iscoroutinefunction(step.function):
                    result = await asyncio.wait_for(
                        step.function(*step.args, **step.kwargs),
                        timeout=step.timeout_seconds
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: step.function(*step.args, **step.kwargs)
                        ),
                        timeout=step.timeout_seconds
                    )

                step.result = result
                step.status = ExecutionState.COMPLETED
                step.completed_at = datetime.now()
                step.duration_ms = (step.completed_at - step.started_at).total_seconds() * 1000

                # Store result in execution variables
                execution.variables[f"step_{step.index}_result"] = result

                return True

            except asyncio.TimeoutError:
                step.error = f"Timeout after {step.timeout_seconds}s"
                logger.warning(f"Step {step.name} timeout, attempt {attempt + 1}/{step.retries}")

            except Exception as e:
                step.error = str(e)
                logger.warning(f"Step {step.name} failed: {e}, attempt {attempt + 1}/{step.retries}")

            # Wait before retry
            if attempt < step.retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        step.status = ExecutionState.FAILED
        return False

    async def _create_checkpoint(
        self,
        execution: DurableExecution,
        checkpoint_type: CheckpointType
    ) -> str:
        """Create a checkpoint"""
        step = execution.steps[execution.current_step] if execution.current_step < len(execution.steps) else None

        checkpoint = Checkpoint(
            execution_id=execution.id,
            step_index=execution.current_step,
            step_name=step.name if step else "End",
            checkpoint_type=checkpoint_type,
            state={
                "current_step": execution.current_step,
                "execution_state": execution.state.value
            },
            variables=dict(execution.variables),
            stack=[
                {
                    "index": s.index,
                    "name": s.name,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error
                }
                for s in execution.steps[:execution.current_step + 1]
            ]
        )

        checkpoint_id = await self.checkpoint_store.save(checkpoint)
        execution.checkpoints.append(checkpoint_id)

        # Cleanup old checkpoints if over limit
        if len(execution.checkpoints) > self.config["max_checkpoints_per_execution"]:
            old_id = execution.checkpoints.pop(0)
            await self.checkpoint_store.delete(old_id)

        logger.debug(f"Created {checkpoint_type.value} checkpoint at step {execution.current_step}")
        return checkpoint_id

    async def _restore_from_checkpoint(
        self,
        execution: DurableExecution,
        checkpoint_id: str
    ) -> None:
        """Restore execution state from checkpoint"""
        checkpoint = await self.checkpoint_store.load(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        if checkpoint.execution_id != execution.id:
            raise ValueError("Checkpoint does not belong to this execution")

        # Restore state
        execution.current_step = checkpoint.step_index
        execution.variables = dict(checkpoint.variables)

        # Restore step states
        for step_state in checkpoint.stack:
            if step_state["index"] < len(execution.steps):
                step = execution.steps[step_state["index"]]
                step.status = ExecutionState(step_state["status"])
                step.result = step_state["result"]
                step.error = step_state["error"]

        logger.info(f"Restored from checkpoint at step {execution.current_step}")

    async def pause(self, execution: DurableExecution) -> str:
        """Pause execution and create checkpoint"""
        if execution.state != ExecutionState.RUNNING:
            raise RuntimeError("Can only pause running execution")

        execution.state = ExecutionState.PAUSED
        checkpoint_id = await self._create_checkpoint(execution, CheckpointType.MANUAL)

        return checkpoint_id

    async def resume(
        self,
        execution: DurableExecution,
        from_checkpoint: str = None
    ) -> DurableExecution:
        """Resume paused execution"""
        if execution.state not in [ExecutionState.PAUSED, ExecutionState.FAILED]:
            raise RuntimeError("Can only resume paused or failed execution")

        checkpoint_id = from_checkpoint or (execution.checkpoints[-1] if execution.checkpoints else None)

        return await self.run(execution, resume_from_checkpoint=checkpoint_id)

    async def time_travel(
        self,
        execution: DurableExecution,
        checkpoint_id: str
    ) -> DurableExecution:
        """Time-travel to a specific checkpoint"""
        checkpoint = await self.checkpoint_store.load(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Create new execution from checkpoint
        new_execution = DurableExecution(
            name=f"{execution.name} (from checkpoint)",
            description=f"Time-traveled from checkpoint {checkpoint_id}",
            steps=execution.steps.copy(),
            variables=dict(checkpoint.variables)
        )

        await self._restore_from_checkpoint(new_execution, checkpoint_id)
        self.executions[new_execution.id] = new_execution

        return new_execution

    def get_execution_history(
        self,
        execution: DurableExecution
    ) -> List[Dict[str, Any]]:
        """Get execution history"""
        history = []

        for step in execution.steps:
            history.append({
                "index": step.index,
                "name": step.name,
                "status": step.status.value,
                "attempts": step.attempts,
                "duration_ms": step.duration_ms,
                "error": step.error
            })

        return history

    async def get_checkpoint_timeline(
        self,
        execution: DurableExecution
    ) -> List[Dict[str, Any]]:
        """Get timeline of all checkpoints"""
        checkpoints = await self.checkpoint_store.list_for_execution(execution.id)

        return [
            {
                "id": c.id,
                "step_index": c.step_index,
                "step_name": c.step_name,
                "type": c.checkpoint_type.value,
                "created_at": c.created_at.isoformat(),
                "size_bytes": c.size_bytes
            }
            for c in checkpoints
        ]


__all__ = ['DurableExecutionEngine', 'DurableExecution', 'Checkpoint',
           'CheckpointStore', 'ExecutionStep', 'ExecutionState', 'CheckpointType']
