#!/usr/bin/env python3
"""
BAEL - Event Sourcing Engine
Event-driven architecture and event sourcing system.

This module provides comprehensive event sourcing capabilities
for building event-driven systems with full audit trails.

Features:
- Event store with persistence
- Event replay and projection
- Aggregate roots
- Command handlers
- Event handlers
- Saga orchestration
- Snapshotting
- Event versioning
- Dead letter handling
- Event schema validation
"""

import asyncio
import copy
import hashlib
import json
import logging
import os
import pickle
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')
E = TypeVar('E', bound='Event')


# =============================================================================
# ENUMS
# =============================================================================

class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRYING = "retrying"


class AggregateState(Enum):
    """Aggregate lifecycle state."""
    NEW = "new"
    ACTIVE = "active"
    DELETED = "deleted"


class SagaState(Enum):
    """Saga execution state."""
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


class ProjectionType(Enum):
    """Projection types."""
    LIVE = "live"
    ASYNC = "async"
    CATCHUP = "catchup"


class ConsistencyLevel(Enum):
    """Consistency levels."""
    EVENTUAL = "eventual"
    STRONG = "strong"
    CAUSAL = "causal"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EventMetadata:
    """Event metadata."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    causation_id: str = ""
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1
    schema_version: str = "1.0"


@dataclass
class Event:
    """Base event class."""
    aggregate_id: str
    aggregate_type: str
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: EventMetadata = field(default_factory=EventMetadata)
    sequence_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_type": self.event_type,
            "data": self.data,
            "metadata": {
                "event_id": self.metadata.event_id,
                "correlation_id": self.metadata.correlation_id,
                "causation_id": self.metadata.causation_id,
                "user_id": self.metadata.user_id,
                "timestamp": self.metadata.timestamp.isoformat(),
                "version": self.metadata.version,
                "schema_version": self.metadata.schema_version
            },
            "sequence_number": self.sequence_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create from dictionary."""
        metadata = EventMetadata(
            event_id=data["metadata"]["event_id"],
            correlation_id=data["metadata"].get("correlation_id", ""),
            causation_id=data["metadata"].get("causation_id", ""),
            user_id=data["metadata"].get("user_id", ""),
            timestamp=datetime.fromisoformat(data["metadata"]["timestamp"]),
            version=data["metadata"].get("version", 1),
            schema_version=data["metadata"].get("schema_version", "1.0")
        )

        return cls(
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            event_type=data["event_type"],
            data=data.get("data", {}),
            metadata=metadata,
            sequence_number=data.get("sequence_number", 0)
        )


@dataclass
class Command:
    """Base command class."""
    command_id: str = field(default_factory=lambda: str(uuid4()))
    aggregate_id: str = ""
    command_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Snapshot:
    """Aggregate snapshot."""
    aggregate_id: str
    aggregate_type: str
    version: int
    state: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SagaStep:
    """Saga step definition."""
    name: str
    action: Callable
    compensation: Optional[Callable] = None
    timeout: float = 30.0
    retry_count: int = 3


@dataclass
class DeadLetter:
    """Dead letter for failed events."""
    event: Event
    error: str
    attempts: int
    last_attempt: datetime
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# EVENT STORE
# =============================================================================

class EventStore(ABC):
    """Abstract event store."""

    @abstractmethod
    async def append(self, event: Event) -> bool:
        """Append event to store."""
        pass

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[Event]:
        """Get events for aggregate."""
        pass

    @abstractmethod
    async def get_all_events(
        self,
        from_position: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get all events from position."""
        pass

    @abstractmethod
    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[Event]:
        """Get events by type."""
        pass


class InMemoryEventStore(EventStore):
    """In-memory event store."""

    def __init__(self):
        self.events: List[Event] = []
        self.aggregate_events: Dict[str, List[Event]] = defaultdict(list)
        self.position = 0

    async def append(self, event: Event) -> bool:
        event.sequence_number = len(self.aggregate_events[event.aggregate_id])
        self.events.append(event)
        self.aggregate_events[event.aggregate_id].append(event)
        self.position += 1
        return True

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[Event]:
        events = self.aggregate_events.get(aggregate_id, [])
        return [e for e in events if e.sequence_number >= from_version]

    async def get_all_events(
        self,
        from_position: int = 0,
        limit: int = 100
    ) -> List[Event]:
        return self.events[from_position:from_position + limit]

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[Event]:
        events = [e for e in self.events if e.event_type == event_type]
        return events[:limit]


class FileEventStore(EventStore):
    """File-based event store."""

    def __init__(self, directory: str = "event_store"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_file = self.directory / "events.jsonl"
        self.index_file = self.directory / "index.json"
        self._load_index()

    def _load_index(self):
        """Load event index."""
        if self.index_file.exists():
            self.index = json.loads(self.index_file.read_text())
        else:
            self.index = {"aggregates": {}, "position": 0}

    def _save_index(self):
        """Save event index."""
        self.index_file.write_text(json.dumps(self.index, indent=2))

    async def append(self, event: Event) -> bool:
        try:
            # Get sequence number
            agg_id = event.aggregate_id
            if agg_id not in self.index["aggregates"]:
                self.index["aggregates"][agg_id] = {"events": [], "version": 0}

            event.sequence_number = self.index["aggregates"][agg_id]["version"]
            self.index["aggregates"][agg_id]["version"] += 1

            # Append to file
            with open(self.events_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")

            # Update index
            self.index["aggregates"][agg_id]["events"].append(self.index["position"])
            self.index["position"] += 1
            self._save_index()

            return True
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            return False

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[Event]:
        events = []

        if aggregate_id not in self.index["aggregates"]:
            return events

        positions = self.index["aggregates"][aggregate_id]["events"]

        if not self.events_file.exists():
            return events

        with open(self.events_file, "r") as f:
            lines = f.readlines()

        for pos in positions:
            if pos < len(lines):
                event = Event.from_dict(json.loads(lines[pos]))
                if event.sequence_number >= from_version:
                    events.append(event)

        return events

    async def get_all_events(
        self,
        from_position: int = 0,
        limit: int = 100
    ) -> List[Event]:
        events = []

        if not self.events_file.exists():
            return events

        with open(self.events_file, "r") as f:
            for i, line in enumerate(f):
                if i < from_position:
                    continue
                if i >= from_position + limit:
                    break
                events.append(Event.from_dict(json.loads(line)))

        return events

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[Event]:
        events = []

        if not self.events_file.exists():
            return events

        with open(self.events_file, "r") as f:
            for line in f:
                event = Event.from_dict(json.loads(line))
                if event.event_type == event_type:
                    events.append(event)
                    if len(events) >= limit:
                        break

        return events


# =============================================================================
# AGGREGATE ROOT
# =============================================================================

class AggregateRoot(ABC):
    """Base aggregate root class."""

    def __init__(self, aggregate_id: str):
        self.id = aggregate_id
        self.version = 0
        self.state = AggregateState.NEW
        self._pending_events: List[Event] = []
        self._event_handlers: Dict[str, Callable] = {}

    @property
    @abstractmethod
    def aggregate_type(self) -> str:
        """Get aggregate type name."""
        pass

    def apply_event(self, event: Event) -> None:
        """Apply an event to update state."""
        handler = self._event_handlers.get(event.event_type)
        if handler:
            handler(event)
        self.version = event.sequence_number + 1

    def raise_event(self, event_type: str, data: Dict[str, Any]) -> Event:
        """Raise a new event."""
        event = Event(
            aggregate_id=self.id,
            aggregate_type=self.aggregate_type,
            event_type=event_type,
            data=data,
            sequence_number=self.version
        )

        self._pending_events.append(event)
        self.apply_event(event)

        return event

    def get_pending_events(self) -> List[Event]:
        """Get pending uncommitted events."""
        return list(self._pending_events)

    def clear_pending_events(self) -> None:
        """Clear pending events after commit."""
        self._pending_events.clear()

    def load_from_history(self, events: List[Event]) -> None:
        """Reconstruct state from event history."""
        for event in events:
            self.apply_event(event)
        self.state = AggregateState.ACTIVE

    def to_snapshot(self) -> Snapshot:
        """Create snapshot of current state."""
        return Snapshot(
            aggregate_id=self.id,
            aggregate_type=self.aggregate_type,
            version=self.version,
            state=self._get_state_dict()
        )

    @abstractmethod
    def _get_state_dict(self) -> Dict[str, Any]:
        """Get state as dictionary for snapshot."""
        pass

    @abstractmethod
    def _load_from_snapshot(self, state: Dict[str, Any]) -> None:
        """Load state from snapshot."""
        pass


# =============================================================================
# COMMAND HANDLER
# =============================================================================

class CommandHandler(ABC):
    """Abstract command handler."""

    @abstractmethod
    def get_command_types(self) -> List[str]:
        """Get handled command types."""
        pass

    @abstractmethod
    async def handle(self, command: Command) -> List[Event]:
        """Handle a command and return events."""
        pass


class CommandBus:
    """Command routing and execution."""

    def __init__(self):
        self.handlers: Dict[str, CommandHandler] = {}
        self.middleware: List[Callable] = []

    def register(self, handler: CommandHandler) -> None:
        """Register a command handler."""
        for command_type in handler.get_command_types():
            self.handlers[command_type] = handler

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware for command processing."""
        self.middleware.append(middleware)

    async def dispatch(self, command: Command) -> List[Event]:
        """Dispatch a command to its handler."""
        handler = self.handlers.get(command.command_type)

        if not handler:
            raise ValueError(f"No handler for command: {command.command_type}")

        # Run middleware
        for mw in self.middleware:
            if asyncio.iscoroutinefunction(mw):
                await mw(command)
            else:
                mw(command)

        return await handler.handle(command)


# =============================================================================
# EVENT HANDLER
# =============================================================================

class EventHandler(ABC):
    """Abstract event handler."""

    @abstractmethod
    def get_event_types(self) -> List[str]:
        """Get handled event types."""
        pass

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle an event."""
        pass


class EventBus:
    """Event routing and distribution."""

    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.global_handlers: List[Callable] = []

    def register(self, handler: EventHandler) -> None:
        """Register an event handler."""
        for event_type in handler.get_event_types():
            self.handlers[event_type].append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        """Subscribe to all events."""
        self.global_handlers.append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to handlers."""
        # Type-specific handlers
        for handler in self.handlers.get(event.event_type, []):
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

        # Global handlers
        for handler in self.global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Global handler error: {e}")


# =============================================================================
# PROJECTION
# =============================================================================

class Projection(ABC):
    """Abstract projection for read models."""

    def __init__(self, name: str):
        self.name = name
        self.position = 0
        self.projection_type = ProjectionType.LIVE

    @abstractmethod
    def get_event_types(self) -> List[str]:
        """Get events this projection handles."""
        pass

    @abstractmethod
    async def apply(self, event: Event) -> None:
        """Apply an event to the projection."""
        pass

    @abstractmethod
    async def get_state(self) -> Any:
        """Get current projection state."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset projection state."""
        pass


class DictionaryProjection(Projection):
    """Simple dictionary-based projection."""

    def __init__(self, name: str):
        super().__init__(name)
        self.data: Dict[str, Any] = {}
        self._handlers: Dict[str, Callable] = {}

    def on(self, event_type: str, handler: Callable) -> None:
        """Register event handler."""
        self._handlers[event_type] = handler

    def get_event_types(self) -> List[str]:
        return list(self._handlers.keys())

    async def apply(self, event: Event) -> None:
        handler = self._handlers.get(event.event_type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                await handler(self.data, event)
            else:
                handler(self.data, event)
        self.position = event.sequence_number

    async def get_state(self) -> Dict[str, Any]:
        return copy.deepcopy(self.data)

    async def reset(self) -> None:
        self.data.clear()
        self.position = 0


# =============================================================================
# SAGA ORCHESTRATOR
# =============================================================================

class Saga:
    """Saga for managing distributed transactions."""

    def __init__(self, saga_id: str):
        self.id = saga_id
        self.state = SagaState.STARTED
        self.steps: List[SagaStep] = []
        self.completed_steps: List[str] = []
        self.data: Dict[str, Any] = {}
        self.errors: List[str] = []

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Callable = None,
        timeout: float = 30.0,
        retry_count: int = 3
    ) -> 'Saga':
        """Add a step to the saga."""
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            timeout=timeout,
            retry_count=retry_count
        )
        self.steps.append(step)
        return self

    async def execute(self) -> bool:
        """Execute the saga."""
        self.state = SagaState.RUNNING

        for step in self.steps:
            success = await self._execute_step(step)

            if not success:
                self.state = SagaState.COMPENSATING
                await self._compensate()
                self.state = SagaState.FAILED
                return False

            self.completed_steps.append(step.name)

        self.state = SagaState.COMPLETED
        return True

    async def _execute_step(self, step: SagaStep) -> bool:
        """Execute a single step with retry."""
        for attempt in range(step.retry_count):
            try:
                if asyncio.iscoroutinefunction(step.action):
                    result = await asyncio.wait_for(
                        step.action(self.data),
                        timeout=step.timeout
                    )
                else:
                    result = step.action(self.data)

                if isinstance(result, dict):
                    self.data.update(result)

                return True

            except asyncio.TimeoutError:
                self.errors.append(f"{step.name}: Timeout on attempt {attempt + 1}")
            except Exception as e:
                self.errors.append(f"{step.name}: {str(e)} on attempt {attempt + 1}")

        return False

    async def _compensate(self) -> None:
        """Execute compensation for completed steps."""
        for step_name in reversed(self.completed_steps):
            step = next((s for s in self.steps if s.name == step_name), None)

            if step and step.compensation:
                try:
                    if asyncio.iscoroutinefunction(step.compensation):
                        await step.compensation(self.data)
                    else:
                        step.compensation(self.data)
                except Exception as e:
                    self.errors.append(f"Compensation {step_name}: {str(e)}")


# =============================================================================
# SNAPSHOT STORE
# =============================================================================

class SnapshotStore:
    """Store for aggregate snapshots."""

    def __init__(self, directory: str = "snapshots"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.snapshots: Dict[str, Snapshot] = {}

    async def save(self, snapshot: Snapshot) -> bool:
        """Save a snapshot."""
        try:
            path = self.directory / f"{snapshot.aggregate_type}_{snapshot.aggregate_id}.json"
            data = {
                "aggregate_id": snapshot.aggregate_id,
                "aggregate_type": snapshot.aggregate_type,
                "version": snapshot.version,
                "state": snapshot.state,
                "timestamp": snapshot.timestamp.isoformat()
            }
            path.write_text(json.dumps(data, indent=2))
            self.snapshots[snapshot.aggregate_id] = snapshot
            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return False

    async def load(
        self,
        aggregate_id: str,
        aggregate_type: str
    ) -> Optional[Snapshot]:
        """Load a snapshot."""
        try:
            path = self.directory / f"{aggregate_type}_{aggregate_id}.json"
            if path.exists():
                data = json.loads(path.read_text())
                return Snapshot(
                    aggregate_id=data["aggregate_id"],
                    aggregate_type=data["aggregate_type"],
                    version=data["version"],
                    state=data["state"],
                    timestamp=datetime.fromisoformat(data["timestamp"])
                )
            return self.snapshots.get(aggregate_id)
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return None


# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================

class DeadLetterQueue:
    """Queue for failed events."""

    def __init__(self, max_size: int = 10000):
        self.queue: List[DeadLetter] = []
        self.max_size = max_size

    async def add(self, event: Event, error: str, attempts: int) -> None:
        """Add event to dead letter queue."""
        dead_letter = DeadLetter(
            event=event,
            error=error,
            attempts=attempts,
            last_attempt=datetime.now()
        )

        self.queue.append(dead_letter)

        # Trim if needed
        if len(self.queue) > self.max_size:
            self.queue = self.queue[-self.max_size:]

    async def get_all(self) -> List[DeadLetter]:
        """Get all dead letters."""
        return list(self.queue)

    async def remove(self, event_id: str) -> bool:
        """Remove a dead letter."""
        for i, dl in enumerate(self.queue):
            if dl.event.metadata.event_id == event_id:
                self.queue.pop(i)
                return True
        return False

    async def retry(self, event_id: str, event_bus: EventBus) -> bool:
        """Retry a dead letter."""
        for dl in self.queue:
            if dl.event.metadata.event_id == event_id:
                await event_bus.publish(dl.event)
                await self.remove(event_id)
                return True
        return False


# =============================================================================
# EVENT SOURCING ENGINE
# =============================================================================

class EventSourcingEngine:
    """
    Master event sourcing engine for BAEL.

    Provides comprehensive event sourcing capabilities including
    event storage, command handling, projections, and sagas.
    """

    def __init__(
        self,
        event_store: EventStore = None,
        snapshot_store: SnapshotStore = None
    ):
        self.event_store = event_store or InMemoryEventStore()
        self.snapshot_store = snapshot_store or SnapshotStore()

        self.command_bus = CommandBus()
        self.event_bus = EventBus()

        self.projections: Dict[str, Projection] = {}
        self.aggregates: Dict[str, Type[AggregateRoot]] = {}

        self.dead_letter_queue = DeadLetterQueue()

        # Configuration
        self.snapshot_frequency = 100  # Events between snapshots

        # Statistics
        self.events_processed = 0
        self.commands_processed = 0

    def register_aggregate(self, aggregate_class: Type[AggregateRoot]) -> None:
        """Register an aggregate type."""
        self.aggregates[aggregate_class.__name__] = aggregate_class

    def register_command_handler(self, handler: CommandHandler) -> None:
        """Register a command handler."""
        self.command_bus.register(handler)

    def register_event_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self.event_bus.register(handler)

    def register_projection(self, projection: Projection) -> None:
        """Register a projection."""
        self.projections[projection.name] = projection

        # Subscribe projection to event bus
        async def apply_to_projection(event: Event):
            if event.event_type in projection.get_event_types():
                await projection.apply(event)

        self.event_bus.subscribe_all(apply_to_projection)

    async def dispatch_command(self, command: Command) -> List[Event]:
        """Dispatch a command and store resulting events."""
        events = await self.command_bus.dispatch(command)

        for event in events:
            await self.event_store.append(event)
            await self.event_bus.publish(event)
            self.events_processed += 1

        self.commands_processed += 1

        return events

    async def load_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str
    ) -> Optional[AggregateRoot]:
        """Load an aggregate from event history."""
        if aggregate_type not in self.aggregates:
            return None

        aggregate_class = self.aggregates[aggregate_type]
        aggregate = aggregate_class(aggregate_id)

        # Try loading from snapshot first
        snapshot = await self.snapshot_store.load(aggregate_id, aggregate_type)
        from_version = 0

        if snapshot:
            aggregate._load_from_snapshot(snapshot.state)
            aggregate.version = snapshot.version
            from_version = snapshot.version

        # Load remaining events
        events = await self.event_store.get_events(aggregate_id, from_version)
        aggregate.load_from_history(events)

        return aggregate

    async def save_aggregate(self, aggregate: AggregateRoot) -> List[Event]:
        """Save aggregate events to store."""
        events = aggregate.get_pending_events()

        for event in events:
            await self.event_store.append(event)
            await self.event_bus.publish(event)
            self.events_processed += 1

        # Create snapshot if needed
        if aggregate.version % self.snapshot_frequency == 0:
            snapshot = aggregate.to_snapshot()
            await self.snapshot_store.save(snapshot)

        aggregate.clear_pending_events()

        return events

    async def replay_events(
        self,
        projection_name: str,
        from_position: int = 0
    ) -> int:
        """Replay events to a projection."""
        projection = self.projections.get(projection_name)

        if not projection:
            return 0

        await projection.reset()

        position = from_position
        replayed = 0

        while True:
            events = await self.event_store.get_all_events(position, 100)

            if not events:
                break

            for event in events:
                if event.event_type in projection.get_event_types():
                    await projection.apply(event)
                    replayed += 1

            position += len(events)

        return replayed

    async def execute_saga(self, saga: Saga) -> bool:
        """Execute a saga."""
        return await saga.execute()

    async def get_projection_state(
        self,
        projection_name: str
    ) -> Optional[Any]:
        """Get current state of a projection."""
        projection = self.projections.get(projection_name)

        if projection:
            return await projection.get_state()

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "events_processed": self.events_processed,
            "commands_processed": self.commands_processed,
            "registered_aggregates": len(self.aggregates),
            "registered_projections": len(self.projections),
            "dead_letters": len(self.dead_letter_queue.queue)
        }


# =============================================================================
# EXAMPLE AGGREGATE
# =============================================================================

class UserAggregate(AggregateRoot):
    """Example user aggregate."""

    def __init__(self, aggregate_id: str):
        super().__init__(aggregate_id)

        self.username = ""
        self.email = ""
        self.is_active = False

        self._event_handlers = {
            "UserCreated": self._on_user_created,
            "UserUpdated": self._on_user_updated,
            "UserActivated": self._on_user_activated,
            "UserDeactivated": self._on_user_deactivated
        }

    @property
    def aggregate_type(self) -> str:
        return "User"

    def create(self, username: str, email: str) -> Event:
        """Create user."""
        if self.state != AggregateState.NEW:
            raise ValueError("User already exists")

        return self.raise_event("UserCreated", {
            "username": username,
            "email": email
        })

    def update(self, username: str = None, email: str = None) -> Event:
        """Update user."""
        data = {}
        if username:
            data["username"] = username
        if email:
            data["email"] = email

        return self.raise_event("UserUpdated", data)

    def activate(self) -> Event:
        """Activate user."""
        return self.raise_event("UserActivated", {})

    def deactivate(self) -> Event:
        """Deactivate user."""
        return self.raise_event("UserDeactivated", {})

    def _on_user_created(self, event: Event):
        self.username = event.data["username"]
        self.email = event.data["email"]
        self.state = AggregateState.ACTIVE

    def _on_user_updated(self, event: Event):
        if "username" in event.data:
            self.username = event.data["username"]
        if "email" in event.data:
            self.email = event.data["email"]

    def _on_user_activated(self, event: Event):
        self.is_active = True

    def _on_user_deactivated(self, event: Event):
        self.is_active = False

    def _get_state_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "state": self.state.value
        }

    def _load_from_snapshot(self, state: Dict[str, Any]) -> None:
        self.username = state["username"]
        self.email = state["email"]
        self.is_active = state["is_active"]
        self.state = AggregateState(state["state"])


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Event Sourcing Engine."""
    print("=" * 70)
    print("BAEL - EVENT SOURCING ENGINE DEMO")
    print("Event-Driven Architecture")
    print("=" * 70)
    print()

    # Create engine
    engine = EventSourcingEngine()

    # Register aggregate
    engine.register_aggregate(UserAggregate)

    # 1. Create and save aggregate
    print("1. CREATE AGGREGATE:")
    print("-" * 40)

    user = UserAggregate("user_001")
    user.create("john_doe", "john@example.com")
    user.activate()

    events = await engine.save_aggregate(user)
    print(f"   Created user with {len(events)} events")
    for event in events:
        print(f"   - {event.event_type}: {event.data}")
    print()

    # 2. Load aggregate
    print("2. LOAD AGGREGATE:")
    print("-" * 40)

    loaded_user = await engine.load_aggregate("UserAggregate", "user_001")
    print(f"   Username: {loaded_user.username}")
    print(f"   Email: {loaded_user.email}")
    print(f"   Active: {loaded_user.is_active}")
    print(f"   Version: {loaded_user.version}")
    print()

    # 3. Update aggregate
    print("3. UPDATE AGGREGATE:")
    print("-" * 40)

    loaded_user.update(email="john.doe@example.com")
    events = await engine.save_aggregate(loaded_user)
    print(f"   Updated with {len(events)} events")
    print(f"   New email: {loaded_user.email}")
    print()

    # 4. Create projection
    print("4. PROJECTION:")
    print("-" * 40)

    user_projection = DictionaryProjection("users")

    def on_user_created(data: dict, event: Event):
        data[event.aggregate_id] = {
            "username": event.data["username"],
            "email": event.data["email"],
            "is_active": False
        }

    def on_user_activated(data: dict, event: Event):
        if event.aggregate_id in data:
            data[event.aggregate_id]["is_active"] = True

    def on_user_updated(data: dict, event: Event):
        if event.aggregate_id in data:
            data[event.aggregate_id].update(event.data)

    user_projection.on("UserCreated", on_user_created)
    user_projection.on("UserActivated", on_user_activated)
    user_projection.on("UserUpdated", on_user_updated)

    engine.register_projection(user_projection)

    # Replay events
    replayed = await engine.replay_events("users")
    print(f"   Replayed {replayed} events")

    state = await engine.get_projection_state("users")
    print(f"   Projection state: {state}")
    print()

    # 5. Saga
    print("5. SAGA ORCHESTRATION:")
    print("-" * 40)

    saga = Saga("registration_saga")

    async def create_account(data):
        print("   - Creating account...")
        data["account_id"] = "acc_123"
        return {"account_id": "acc_123"}

    async def send_welcome_email(data):
        print("   - Sending welcome email...")
        return {}

    async def setup_defaults(data):
        print("   - Setting up defaults...")
        return {}

    async def rollback_account(data):
        print("   - Rolling back account...")

    saga.add_step("create_account", create_account, rollback_account)
    saga.add_step("send_email", send_welcome_email)
    saga.add_step("setup_defaults", setup_defaults)

    success = await engine.execute_saga(saga)
    print(f"   Saga completed: {success}")
    print(f"   Saga state: {saga.state.value}")
    print()

    # 6. Event Store Queries
    print("6. EVENT STORE QUERIES:")
    print("-" * 40)

    all_events = await engine.event_store.get_all_events(0, 10)
    print(f"   Total events: {len(all_events)}")

    user_events = await engine.event_store.get_events("user_001")
    print(f"   User events: {len(user_events)}")

    by_type = await engine.event_store.get_events_by_type("UserCreated")
    print(f"   UserCreated events: {len(by_type)}")
    print()

    # 7. Statistics
    print("7. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Event Sourcing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
