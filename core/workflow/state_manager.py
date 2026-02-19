"""
BAEL State Manager
===================

State management and checkpointing for workflows.
Enables resume and recovery.

Features:
- State persistence
- Checkpointing
- State recovery
- History tracking
- Distributed state
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workflow_node import NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """Complete state of a workflow execution."""
    execution_id: str
    workflow_id: str

    # Node states
    node_statuses: Dict[str, NodeStatus] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    node_attempts: Dict[str, int] = field(default_factory=dict)

    # Variables
    variables: Dict[str, Any] = field(default_factory=dict)

    # Progress
    current_level: int = 0
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 0


@dataclass
class Checkpoint:
    """A checkpoint of workflow state."""
    id: str
    execution_id: str

    # State snapshot
    state: WorkflowState = field(default_factory=lambda: WorkflowState(
        execution_id="", workflow_id=""
    ))

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    reason: str = ""

    # Validation
    checksum: str = ""


class StateStore:
    """
    Abstract state store interface.
    """

    async def save(self, key: str, data: Any) -> None:
        """Save data."""
        raise NotImplementedError

    async def load(self, key: str) -> Optional[Any]:
        """Load data."""
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        """Delete data."""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        raise NotImplementedError

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys with prefix."""
        raise NotImplementedError


class FileStateStore(StateStore):
    """File-based state store."""

    def __init__(self, base_dir: str = "./state"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get file path for key."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_key}.pkl"

    async def save(self, key: str, data: Any) -> None:
        """Save data to file."""
        path = self._get_path(key)
        with open(path, 'wb') as f:
            pickle.dump(data, f)

    async def load(self, key: str) -> Optional[Any]:
        """Load data from file."""
        path = self._get_path(key)
        if not path.exists():
            return None
        with open(path, 'rb') as f:
            return pickle.load(f)

    async def delete(self, key: str) -> None:
        """Delete file."""
        path = self._get_path(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        return self._get_path(key).exists()

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List files with prefix."""
        keys = []
        for path in self.base_dir.glob(f"{prefix}*.pkl"):
            keys.append(path.stem)
        return keys


class MemoryStateStore(StateStore):
    """In-memory state store."""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    async def save(self, key: str, data: Any) -> None:
        self._data[key] = data

    async def load(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def list_keys(self, prefix: str = "") -> List[str]:
        return [k for k in self._data.keys() if k.startswith(prefix)]


class StateManager:
    """
    State manager for BAEL workflows.

    Manages state persistence and recovery.
    """

    def __init__(
        self,
        store: Optional[StateStore] = None,
        checkpoint_interval: int = 5,
        max_checkpoints: int = 10,
    ):
        self.store = store or MemoryStateStore()
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints

        # Current states
        self._states: Dict[str, WorkflowState] = {}

        # Stats
        self.stats = {
            "states_saved": 0,
            "states_loaded": 0,
            "checkpoints_created": 0,
        }

    async def create_state(
        self,
        execution_id: str,
        workflow_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        """
        Create a new workflow state.

        Args:
            execution_id: Execution identifier
            workflow_id: Workflow identifier
            variables: Initial variables

        Returns:
            New workflow state
        """
        state = WorkflowState(
            execution_id=execution_id,
            workflow_id=workflow_id,
            variables=variables or {},
        )

        self._states[execution_id] = state
        await self._save_state(state)

        return state

    async def update_state(
        self,
        execution_id: str,
        node_id: str,
        status: NodeStatus,
        output: Optional[Any] = None,
        attempt: int = 1,
    ) -> None:
        """
        Update workflow state after node execution.

        Args:
            execution_id: Execution identifier
            node_id: Node that was executed
            status: Node status
            output: Node output
            attempt: Execution attempt
        """
        state = self._states.get(execution_id)
        if not state:
            return

        state.node_statuses[node_id] = status
        state.node_attempts[node_id] = attempt

        if output is not None:
            state.node_outputs[node_id] = output

        if status == NodeStatus.COMPLETED:
            if node_id not in state.completed_nodes:
                state.completed_nodes.append(node_id)
        elif status == NodeStatus.FAILED:
            if node_id not in state.failed_nodes:
                state.failed_nodes.append(node_id)

        state.last_updated = datetime.now()
        state.version += 1

        # Auto-checkpoint
        if state.version % self.checkpoint_interval == 0:
            await self.create_checkpoint(execution_id, "Auto checkpoint")

        await self._save_state(state)

    async def get_state(self, execution_id: str) -> Optional[WorkflowState]:
        """Get workflow state."""
        if execution_id in self._states:
            return self._states[execution_id]

        # Try loading from store
        state = await self._load_state(execution_id)
        if state:
            self._states[execution_id] = state

        return state

    async def _save_state(self, state: WorkflowState) -> None:
        """Save state to store."""
        key = f"state:{state.execution_id}"
        await self.store.save(key, state)
        self.stats["states_saved"] += 1

    async def _load_state(self, execution_id: str) -> Optional[WorkflowState]:
        """Load state from store."""
        key = f"state:{execution_id}"
        state = await self.store.load(key)
        if state:
            self.stats["states_loaded"] += 1
        return state

    async def create_checkpoint(
        self,
        execution_id: str,
        reason: str = "",
    ) -> Optional[Checkpoint]:
        """
        Create a checkpoint of current state.

        Args:
            execution_id: Execution identifier
            reason: Reason for checkpoint

        Returns:
            Checkpoint or None if state not found
        """
        state = await self.get_state(execution_id)
        if not state:
            return None

        checkpoint_id = hashlib.md5(
            f"{execution_id}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Create checksum
        state_str = json.dumps({
            "completed": state.completed_nodes,
            "failed": state.failed_nodes,
            "version": state.version,
        }, sort_keys=True)
        checksum = hashlib.sha256(state_str.encode()).hexdigest()[:16]

        checkpoint = Checkpoint(
            id=checkpoint_id,
            execution_id=execution_id,
            state=state,
            reason=reason,
            checksum=checksum,
        )

        # Save checkpoint
        key = f"checkpoint:{execution_id}:{checkpoint_id}"
        await self.store.save(key, checkpoint)

        # Cleanup old checkpoints
        await self._cleanup_checkpoints(execution_id)

        self.stats["checkpoints_created"] += 1

        return checkpoint

    async def get_checkpoints(
        self,
        execution_id: str,
    ) -> List[Checkpoint]:
        """Get all checkpoints for an execution."""
        prefix = f"checkpoint:{execution_id}:"
        keys = await self.store.list_keys(prefix)

        checkpoints = []
        for key in keys:
            checkpoint = await self.store.load(key)
            if checkpoint:
                checkpoints.append(checkpoint)

        # Sort by creation time
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)

        return checkpoints

    async def restore_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> WorkflowState:
        """
        Restore state from checkpoint.

        Args:
            checkpoint: Checkpoint to restore

        Returns:
            Restored state
        """
        state = checkpoint.state
        state.last_updated = datetime.now()

        self._states[state.execution_id] = state
        await self._save_state(state)

        return state

    async def _cleanup_checkpoints(
        self,
        execution_id: str,
    ) -> None:
        """Cleanup old checkpoints."""
        checkpoints = await self.get_checkpoints(execution_id)

        if len(checkpoints) > self.max_checkpoints:
            # Delete oldest
            for checkpoint in checkpoints[self.max_checkpoints:]:
                key = f"checkpoint:{execution_id}:{checkpoint.id}"
                await self.store.delete(key)

    async def get_resume_point(
        self,
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Get resume point for failed execution.

        Returns:
            Resume information
        """
        state = await self.get_state(execution_id)
        if not state:
            return {"can_resume": False}

        return {
            "can_resume": True,
            "completed_nodes": state.completed_nodes,
            "failed_nodes": state.failed_nodes,
            "current_level": state.current_level,
            "last_updated": state.last_updated,
        }

    async def clear_state(self, execution_id: str) -> None:
        """Clear state for execution."""
        self._states.pop(execution_id, None)

        key = f"state:{execution_id}"
        await self.store.delete(key)

        # Delete checkpoints
        checkpoints = await self.get_checkpoints(execution_id)
        for checkpoint in checkpoints:
            ck_key = f"checkpoint:{execution_id}:{checkpoint.id}"
            await self.store.delete(ck_key)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "active_states": len(self._states),
        }


def demo():
    """Demonstrate state manager."""
    import asyncio

    print("=" * 60)
    print("BAEL State Manager Demo")
    print("=" * 60)

    async def run():
        # Create manager with file store
        store = MemoryStateStore()
        manager = StateManager(
            store=store,
            checkpoint_interval=2,
            max_checkpoints=5,
        )

        # Create state
        print("\nCreating workflow state...")
        state = await manager.create_state(
            execution_id="exec_001",
            workflow_id="workflow_001",
            variables={"env": "production"},
        )
        print(f"  State created: {state.execution_id}")

        # Simulate node executions
        print("\nSimulating node executions...")

        nodes = ["fetch", "process", "transform", "validate", "save"]

        for i, node in enumerate(nodes):
            status = NodeStatus.COMPLETED if i < 4 else NodeStatus.FAILED
            output = {"result": f"{node}_output"}

            await manager.update_state(
                execution_id="exec_001",
                node_id=node,
                status=status,
                output=output,
            )
            print(f"  {node}: {status.value}")

        # Get checkpoints
        print("\nCheckpoints:")
        checkpoints = await manager.get_checkpoints("exec_001")
        for cp in checkpoints:
            print(f"  - {cp.id}: {cp.reason} ({cp.created_at})")

        # Get resume point
        print("\nResume point:")
        resume = await manager.get_resume_point("exec_001")
        print(f"  Can resume: {resume['can_resume']}")
        print(f"  Completed: {resume['completed_nodes']}")
        print(f"  Failed: {resume['failed_nodes']}")

        # Restore from checkpoint
        if checkpoints:
            print("\nRestoring from checkpoint...")
            restored = await manager.restore_checkpoint(checkpoints[0])
            print(f"  Restored version: {restored.version}")

        print(f"\nStats: {manager.get_stats()}")

    asyncio.run(run())


if __name__ == "__main__":
    demo()
