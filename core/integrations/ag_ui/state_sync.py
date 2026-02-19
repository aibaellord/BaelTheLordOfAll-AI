"""
BAEL AG-UI State Synchronization
=================================

Real-time state synchronization between agent and frontend.
Uses JSON Patch for efficient delta updates.

Features:
- Full state snapshots
- Delta updates (JSON Patch)
- Optimistic updates
- Conflict resolution
- Sync strategies
"""

import asyncio
import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SyncStrategy(Enum):
    """State synchronization strategies."""
    SNAPSHOT = "snapshot"         # Always send full state
    DELTA = "delta"               # Send only changes
    HYBRID = "hybrid"             # Delta normally, snapshot periodically
    ON_DEMAND = "on_demand"       # Only sync when requested


class OperationType(Enum):
    """JSON Patch operation types."""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"


@dataclass
class StateChange:
    """A state change operation (JSON Patch format)."""
    op: OperationType
    path: str
    value: Any = None
    from_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON Patch operation."""
        result = {
            "op": self.op.value,
            "path": self.path,
        }

        if self.op in (OperationType.ADD, OperationType.REPLACE, OperationType.TEST):
            result["value"] = self.value

        if self.op in (OperationType.MOVE, OperationType.COPY):
            result["from"] = self.from_path

        return result


@dataclass
class StateVersion:
    """State version information."""
    version: int
    timestamp: datetime
    checksum: str

    @staticmethod
    def compute_checksum(state: Dict[str, Any]) -> str:
        """Compute state checksum."""
        import hashlib
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]


class StateSync:
    """
    State synchronization manager for AG-UI.
    """

    def __init__(
        self,
        strategy: SyncStrategy = SyncStrategy.HYBRID,
        snapshot_interval: int = 10,
    ):
        self.strategy = strategy
        self.snapshot_interval = snapshot_interval

        # State tracking
        self.current_state: Dict[str, Any] = {}
        self.previous_state: Dict[str, Any] = {}
        self.state_history: List[Dict[str, Any]] = []

        # Versioning
        self.version = 0
        self.last_snapshot_version = 0

        # Pending changes
        self.pending_changes: List[StateChange] = []

        # Callbacks
        self.change_callbacks: List[Callable[[List[StateChange]], None]] = []
        self.snapshot_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def set_state(
        self,
        state: Dict[str, Any],
        notify: bool = True,
    ) -> int:
        """
        Set the full state.

        Args:
            state: New state
            notify: Whether to notify callbacks

        Returns:
            New version number
        """
        self.previous_state = copy.deepcopy(self.current_state)
        self.current_state = copy.deepcopy(state)
        self.version += 1

        if notify:
            self._notify_snapshot()

        return self.version

    def update(
        self,
        path: str,
        value: Any,
        operation: OperationType = OperationType.REPLACE,
    ) -> StateChange:
        """
        Update state at path.

        Args:
            path: JSON pointer path (e.g., "/foo/bar")
            value: New value
            operation: Operation type

        Returns:
            State change object
        """
        change = StateChange(op=operation, path=path, value=value)

        # Apply change
        self._apply_change(change)
        self.version += 1

        # Track change
        self.pending_changes.append(change)

        # Notify
        if self.strategy in (SyncStrategy.DELTA, SyncStrategy.HYBRID):
            self._notify_delta([change])

        return change

    def update_many(
        self,
        changes: List[Dict[str, Any]],
    ) -> List[StateChange]:
        """
        Apply multiple changes.

        Args:
            changes: List of change dicts with op, path, value

        Returns:
            List of StateChange objects
        """
        state_changes = []

        for change_dict in changes:
            op = OperationType(change_dict["op"])
            path = change_dict["path"]
            value = change_dict.get("value")
            from_path = change_dict.get("from")

            change = StateChange(
                op=op,
                path=path,
                value=value,
                from_path=from_path,
            )

            self._apply_change(change)
            state_changes.append(change)

        self.version += 1
        self.pending_changes.extend(state_changes)

        if self.strategy in (SyncStrategy.DELTA, SyncStrategy.HYBRID):
            self._notify_delta(state_changes)

        return state_changes

    def _apply_change(self, change: StateChange) -> None:
        """Apply a change to current state."""
        path_parts = change.path.split("/")[1:]  # Remove empty first element

        if not path_parts or path_parts == [""]:
            # Root path
            if change.op == OperationType.REPLACE:
                self.current_state = change.value
            return

        # Navigate to parent
        parent = self.current_state
        for part in path_parts[:-1]:
            if isinstance(parent, dict):
                if part not in parent:
                    parent[part] = {}
                parent = parent[part]
            elif isinstance(parent, list):
                idx = int(part)
                parent = parent[idx]

        key = path_parts[-1]

        if change.op == OperationType.ADD:
            if isinstance(parent, dict):
                parent[key] = change.value
            elif isinstance(parent, list):
                if key == "-":
                    parent.append(change.value)
                else:
                    parent.insert(int(key), change.value)

        elif change.op == OperationType.REMOVE:
            if isinstance(parent, dict):
                parent.pop(key, None)
            elif isinstance(parent, list):
                parent.pop(int(key))

        elif change.op == OperationType.REPLACE:
            if isinstance(parent, dict):
                parent[key] = change.value
            elif isinstance(parent, list):
                parent[int(key)] = change.value

    def get_value(self, path: str) -> Any:
        """Get value at path."""
        if not path or path == "/":
            return self.current_state

        path_parts = path.split("/")[1:]
        value = self.current_state

        for part in path_parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list):
                value = value[int(part)]

            if value is None:
                return None

        return value

    def compute_diff(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        path: str = "",
    ) -> List[StateChange]:
        """
        Compute diff between two states.

        Args:
            old_state: Previous state
            new_state: Current state
            path: Current path prefix

        Returns:
            List of changes
        """
        changes = []

        # Handle None states
        if old_state is None:
            if new_state is not None:
                changes.append(StateChange(
                    op=OperationType.ADD,
                    path=path or "/",
                    value=new_state,
                ))
            return changes

        if new_state is None:
            changes.append(StateChange(
                op=OperationType.REMOVE,
                path=path or "/",
            ))
            return changes

        # Handle different types
        if type(old_state) != type(new_state):
            changes.append(StateChange(
                op=OperationType.REPLACE,
                path=path or "/",
                value=new_state,
            ))
            return changes

        # Handle dicts
        if isinstance(old_state, dict):
            all_keys = set(old_state.keys()) | set(new_state.keys())

            for key in all_keys:
                key_path = f"{path}/{key}"

                if key not in old_state:
                    changes.append(StateChange(
                        op=OperationType.ADD,
                        path=key_path,
                        value=new_state[key],
                    ))
                elif key not in new_state:
                    changes.append(StateChange(
                        op=OperationType.REMOVE,
                        path=key_path,
                    ))
                else:
                    changes.extend(self.compute_diff(
                        old_state[key],
                        new_state[key],
                        key_path,
                    ))

        # Handle lists
        elif isinstance(old_state, list):
            if old_state != new_state:
                # For simplicity, replace entire list
                changes.append(StateChange(
                    op=OperationType.REPLACE,
                    path=path or "/",
                    value=new_state,
                ))

        # Handle primitives
        elif old_state != new_state:
            changes.append(StateChange(
                op=OperationType.REPLACE,
                path=path or "/",
                value=new_state,
            ))

        return changes

    def get_snapshot(self) -> Dict[str, Any]:
        """Get full state snapshot."""
        self.last_snapshot_version = self.version
        return copy.deepcopy(self.current_state)

    def get_pending_delta(self) -> List[Dict[str, Any]]:
        """Get pending delta changes."""
        delta = [c.to_dict() for c in self.pending_changes]
        self.pending_changes.clear()
        return delta

    def should_snapshot(self) -> bool:
        """Check if snapshot should be sent."""
        if self.strategy == SyncStrategy.SNAPSHOT:
            return True

        if self.strategy == SyncStrategy.HYBRID:
            return (self.version - self.last_snapshot_version) >= self.snapshot_interval

        return False

    def _notify_delta(self, changes: List[StateChange]) -> None:
        """Notify delta callbacks."""
        for callback in self.change_callbacks:
            try:
                callback(changes)
            except Exception as e:
                logger.error(f"Delta callback error: {e}")

    def _notify_snapshot(self) -> None:
        """Notify snapshot callbacks."""
        for callback in self.snapshot_callbacks:
            try:
                callback(self.get_snapshot())
            except Exception as e:
                logger.error(f"Snapshot callback error: {e}")

    def on_change(self, callback: Callable[[List[StateChange]], None]) -> None:
        """Register change callback."""
        self.change_callbacks.append(callback)

    def on_snapshot(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register snapshot callback."""
        self.snapshot_callbacks.append(callback)

    def get_version_info(self) -> StateVersion:
        """Get current version information."""
        return StateVersion(
            version=self.version,
            timestamp=datetime.now(),
            checksum=StateVersion.compute_checksum(self.current_state),
        )


def demo():
    """Demonstrate state sync."""
    print("=" * 60)
    print("BAEL AG-UI State Sync Demo")
    print("=" * 60)

    sync = StateSync(strategy=SyncStrategy.DELTA)

    # Register callbacks
    def on_change(changes):
        print(f"  Delta: {[c.to_dict() for c in changes]}")

    sync.on_change(on_change)

    # Set initial state
    sync.set_state({"counter": 0, "messages": []})

    # Make updates
    print("\nMaking updates:")
    sync.update("/counter", 1)
    sync.update("/messages/-", "Hello", operation=OperationType.ADD)
    sync.update("/messages/-", "World", operation=OperationType.ADD)

    print(f"\nFinal state: {sync.get_snapshot()}")
    print(f"Version: {sync.version}")


if __name__ == "__main__":
    demo()
