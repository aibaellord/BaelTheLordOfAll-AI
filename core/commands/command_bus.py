#!/usr/bin/env python3
"""
BAEL - Command Bus & CQRS System
Comprehensive command query responsibility segregation.

This module provides a complete CQRS implementation with
command bus, query bus, and event bus patterns.

Features:
- Command bus with handlers
- Query bus for reads
- Event dispatching
- Middleware pipeline
- Saga orchestration
- Command validation
- Retry mechanisms
- Audit logging
- Async execution
- Compensation logic
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
TCommand = TypeVar('TCommand', bound='Command')
TQuery = TypeVar('TQuery', bound='Query')
TResult = TypeVar('TResult')


# =============================================================================
# ENUMS
# =============================================================================

class CommandStatus(Enum):
    """Command execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MiddlewarePosition(Enum):
    """Middleware position in pipeline."""
    BEFORE = "before"
    AFTER = "after"


class SagaStatus(Enum):
    """Saga execution status."""
    STARTED = "started"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


# =============================================================================
# BASE CLASSES
# =============================================================================

@dataclass
class Command:
    """Base command class."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_name(self) -> str:
        return self.__class__.__name__


@dataclass
class Query:
    """Base query class."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    @property
    def query_name(self) -> str:
        return self.__class__.__name__


@dataclass
class Event:
    """Base event class."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    aggregate_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        return self.__class__.__name__


@dataclass
class CommandResult(Generic[T]):
    """Result of command execution."""
    command_id: str
    status: CommandStatus
    data: Optional[T] = None
    error: Optional[str] = None
    events: List[Event] = field(default_factory=list)
    execution_time_ms: float = 0

    @property
    def is_success(self) -> bool:
        return self.status == CommandStatus.COMPLETED


@dataclass
class QueryResult(Generic[T]):
    """Result of query execution."""
    query_id: str
    data: Optional[T] = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    from_cache: bool = False


@dataclass
class CommandContext:
    """Context for command execution."""
    command: Command
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# HANDLERS
# =============================================================================

class CommandHandler(ABC, Generic[TCommand, TResult]):
    """Abstract command handler."""

    @abstractmethod
    async def handle(self, command: TCommand, context: CommandContext) -> TResult:
        pass


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Abstract query handler."""

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        pass


class EventHandler(ABC):
    """Abstract event handler."""

    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass


class FunctionCommandHandler(CommandHandler[TCommand, TResult]):
    """Function-based command handler."""

    def __init__(self, func: Callable[[TCommand, CommandContext], Awaitable[TResult]]):
        self.func = func

    async def handle(self, command: TCommand, context: CommandContext) -> TResult:
        return await self.func(command, context)


class FunctionQueryHandler(QueryHandler[TQuery, TResult]):
    """Function-based query handler."""

    def __init__(self, func: Callable[[TQuery], Awaitable[TResult]]):
        self.func = func

    async def handle(self, query: TQuery) -> TResult:
        return await self.func(query)


# =============================================================================
# MIDDLEWARE
# =============================================================================

class Middleware(ABC):
    """Abstract middleware."""

    @abstractmethod
    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable[[Command, CommandContext], Awaitable[Any]]
    ) -> Any:
        pass


class LoggingMiddleware(Middleware):
    """Logs command execution."""

    def __init__(self, log_result: bool = False):
        self.log_result = log_result

    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable
    ) -> Any:
        logger.info(f"Executing command: {command.command_name} [{command.command_id}]")
        start = time.time()

        try:
            result = await next_handler(command, context)
            duration = (time.time() - start) * 1000
            logger.info(f"Command completed in {duration:.2f}ms")

            if self.log_result:
                logger.debug(f"Result: {result}")

            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"Command failed after {duration:.2f}ms: {e}")
            raise


class ValidationMiddleware(Middleware):
    """Validates commands before execution."""

    def __init__(self):
        self.validators: Dict[Type[Command], List[Callable]] = {}

    def register_validator(
        self,
        command_type: Type[Command],
        validator: Callable[[Command], bool]
    ) -> None:
        if command_type not in self.validators:
            self.validators[command_type] = []
        self.validators[command_type].append(validator)

    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable
    ) -> Any:
        validators = self.validators.get(type(command), [])

        for validator in validators:
            if asyncio.iscoroutinefunction(validator):
                valid = await validator(command)
            else:
                valid = validator(command)

            if not valid:
                raise ValueError(f"Command validation failed: {command.command_name}")

        return await next_handler(command, context)


class RetryMiddleware(Middleware):
    """Retries failed commands."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        exponential_backoff: bool = True
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff

    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable
    ) -> Any:
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await next_handler(command, context)
            except Exception as e:
                last_error = e

                if attempt < self.max_retries:
                    delay = self.retry_delay
                    if self.exponential_backoff:
                        delay *= (2 ** attempt)

                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} "
                        f"for {command.command_name} after {delay}s"
                    )
                    await asyncio.sleep(delay)

        raise last_error


class AuditMiddleware(Middleware):
    """Audits command execution."""

    def __init__(self, max_entries: int = 10000):
        self.audit_log: deque = deque(maxlen=max_entries)

    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable
    ) -> Any:
        entry = {
            "command_id": command.command_id,
            "command_name": command.command_name,
            "user_id": context.user_id,
            "timestamp": time.time(),
            "correlation_id": context.correlation_id
        }

        try:
            result = await next_handler(command, context)
            entry["status"] = "success"
            entry["result"] = str(result)[:200] if result else None
            return result
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            raise
        finally:
            self.audit_log.append(entry)

    def get_audit_log(
        self,
        user_id: str = None,
        command_name: str = None,
        limit: int = 100
    ) -> List[Dict]:
        entries = list(self.audit_log)

        if user_id:
            entries = [e for e in entries if e.get("user_id") == user_id]

        if command_name:
            entries = [e for e in entries if e.get("command_name") == command_name]

        return entries[-limit:]


class IdempotencyMiddleware(Middleware):
    """Ensures idempotent command execution."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}

    def _get_key(self, command: Command) -> str:
        data = json.dumps({
            "type": command.command_name,
            "data": command.__dict__
        }, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    async def execute(
        self,
        command: Command,
        context: CommandContext,
        next_handler: Callable
    ) -> Any:
        key = self._get_key(command)
        current_time = time.time()

        # Check cache
        if key in self.cache:
            result, timestamp = self.cache[key]
            if current_time - timestamp < self.ttl:
                logger.info(f"Returning cached result for {command.command_name}")
                return result

        # Execute and cache
        result = await next_handler(command, context)
        self.cache[key] = (result, current_time)

        # Cleanup old entries
        expired_keys = [
            k for k, (_, ts) in self.cache.items()
            if current_time - ts >= self.ttl
        ]
        for k in expired_keys:
            del self.cache[k]

        return result


# =============================================================================
# COMMAND BUS
# =============================================================================

class CommandBus:
    """
    Command bus for dispatching commands to handlers.
    """

    def __init__(self):
        self.handlers: Dict[Type[Command], CommandHandler] = {}
        self.middleware: List[Middleware] = []
        self.execution_count = 0
        self.error_count = 0

    def register(
        self,
        command_type: Type[TCommand],
        handler: Union[CommandHandler[TCommand, Any], Callable]
    ) -> None:
        """Register a command handler."""
        if callable(handler) and not isinstance(handler, CommandHandler):
            handler = FunctionCommandHandler(handler)

        self.handlers[command_type] = handler
        logger.debug(f"Registered handler for {command_type.__name__}")

    def use(self, middleware: Middleware) -> 'CommandBus':
        """Add middleware to pipeline."""
        self.middleware.append(middleware)
        return self

    async def dispatch(
        self,
        command: Command,
        user_id: str = None,
        correlation_id: str = None
    ) -> CommandResult:
        """Dispatch a command."""
        self.execution_count += 1
        start_time = time.time()
        events: List[Event] = []

        context = CommandContext(
            command=command,
            user_id=user_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=command.command_id
        )

        handler = self.handlers.get(type(command))
        if not handler:
            self.error_count += 1
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=f"No handler for {command.command_name}"
            )

        try:
            # Build pipeline
            async def execute(cmd: Command, ctx: CommandContext) -> Any:
                return await handler.handle(cmd, ctx)

            pipeline = execute

            for mw in reversed(self.middleware):
                prev = pipeline
                pipeline = lambda c, ctx, m=mw, p=prev: m.execute(c, ctx, p)

            result = await pipeline(command, context)

            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.COMPLETED,
                data=result,
                events=events,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            self.error_count += 1
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def handler(
        self,
        command_type: Type[TCommand]
    ) -> Callable[[Callable], Callable]:
        """Decorator to register command handler."""
        def decorator(func: Callable) -> Callable:
            self.register(command_type, func)
            return func
        return decorator


# =============================================================================
# QUERY BUS
# =============================================================================

class QueryBus:
    """
    Query bus for dispatching queries to handlers.
    """

    def __init__(self):
        self.handlers: Dict[Type[Query], QueryHandler] = {}
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_ttl: float = 60.0
        self.execution_count = 0

    def register(
        self,
        query_type: Type[TQuery],
        handler: Union[QueryHandler[TQuery, Any], Callable]
    ) -> None:
        """Register a query handler."""
        if callable(handler) and not isinstance(handler, QueryHandler):
            handler = FunctionQueryHandler(handler)

        self.handlers[query_type] = handler

    def set_cache_ttl(self, ttl: float) -> None:
        """Set cache TTL in seconds."""
        self.cache_ttl = ttl

    def _get_cache_key(self, query: Query) -> str:
        data = json.dumps(query.__dict__, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    async def query(
        self,
        query: Query,
        use_cache: bool = False
    ) -> QueryResult:
        """Execute a query."""
        self.execution_count += 1
        start_time = time.time()

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(query)
            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return QueryResult(
                        query_id=query.query_id,
                        data=result,
                        from_cache=True
                    )

        handler = self.handlers.get(type(query))
        if not handler:
            return QueryResult(
                query_id=query.query_id,
                error=f"No handler for {query.query_name}"
            )

        try:
            result = await handler.handle(query)

            # Cache result
            if use_cache:
                self.cache[cache_key] = (result, time.time())

            return QueryResult(
                query_id=query.query_id,
                data=result,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return QueryResult(
                query_id=query.query_id,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def handler(
        self,
        query_type: Type[TQuery]
    ) -> Callable[[Callable], Callable]:
        """Decorator to register query handler."""
        def decorator(func: Callable) -> Callable:
            self.register(query_type, func)
            return func
        return decorator


# =============================================================================
# EVENT BUS
# =============================================================================

class EventBus:
    """
    Event bus for publishing domain events.
    """

    def __init__(self):
        self.handlers: Dict[Type[Event], List[EventHandler]] = defaultdict(list)
        self.global_handlers: List[EventHandler] = []
        self.event_history: deque = deque(maxlen=10000)
        self.publish_count = 0

    def subscribe(
        self,
        event_type: Type[Event],
        handler: Union[EventHandler, Callable]
    ) -> None:
        """Subscribe to an event type."""
        if callable(handler) and not isinstance(handler, EventHandler):
            class FuncHandler(EventHandler):
                def __init__(self, func):
                    self.func = func

                async def handle(self, event: Event):
                    if asyncio.iscoroutinefunction(self.func):
                        await self.func(event)
                    else:
                        self.func(event)

            handler = FuncHandler(handler)

        self.handlers[event_type].append(handler)

    def subscribe_all(self, handler: Union[EventHandler, Callable]) -> None:
        """Subscribe to all events."""
        if callable(handler) and not isinstance(handler, EventHandler):
            class FuncHandler(EventHandler):
                def __init__(self, func):
                    self.func = func

                async def handle(self, event: Event):
                    if asyncio.iscoroutinefunction(self.func):
                        await self.func(event)
                    else:
                        self.func(event)

            handler = FuncHandler(handler)

        self.global_handlers.append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event."""
        self.publish_count += 1
        self.event_history.append(event)

        handlers = self.handlers.get(type(event), []) + self.global_handlers

        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def publish_many(self, events: List[Event]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)

    def get_history(
        self,
        event_type: Type[Event] = None,
        aggregate_id: str = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history."""
        events = list(self.event_history)

        if event_type:
            events = [e for e in events if isinstance(e, event_type)]

        if aggregate_id:
            events = [e for e in events if e.aggregate_id == aggregate_id]

        return events[-limit:]


# =============================================================================
# SAGA
# =============================================================================

@dataclass
class SagaStep:
    """A step in a saga."""
    name: str
    execute: Callable[[], Awaitable[Any]]
    compensate: Callable[[], Awaitable[None]]
    result: Optional[Any] = None
    status: CommandStatus = CommandStatus.PENDING


class Saga:
    """
    Saga for orchestrating distributed transactions.
    """

    def __init__(self, saga_id: str = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.status = SagaStatus.STARTED
        self.current_step = 0
        self.error: Optional[str] = None

    def add_step(
        self,
        name: str,
        execute: Callable[[], Awaitable[Any]],
        compensate: Callable[[], Awaitable[None]]
    ) -> 'Saga':
        """Add a step to the saga."""
        self.steps.append(SagaStep(
            name=name,
            execute=execute,
            compensate=compensate
        ))
        return self

    async def execute(self) -> bool:
        """Execute the saga."""
        self.status = SagaStatus.EXECUTING

        try:
            for i, step in enumerate(self.steps):
                self.current_step = i
                logger.info(f"Saga {self.saga_id}: Executing step '{step.name}'")

                try:
                    step.result = await step.execute()
                    step.status = CommandStatus.COMPLETED
                except Exception as e:
                    step.status = CommandStatus.FAILED
                    self.error = str(e)
                    logger.error(f"Saga step '{step.name}' failed: {e}")

                    # Start compensation
                    await self._compensate(i - 1)
                    return False

            self.status = SagaStatus.COMPLETED
            return True

        except Exception as e:
            self.status = SagaStatus.FAILED
            self.error = str(e)
            return False

    async def _compensate(self, from_step: int) -> None:
        """Compensate executed steps."""
        self.status = SagaStatus.COMPENSATING

        for i in range(from_step, -1, -1):
            step = self.steps[i]

            if step.status == CommandStatus.COMPLETED:
                logger.info(f"Saga {self.saga_id}: Compensating step '{step.name}'")

                try:
                    await step.compensate()
                    step.status = CommandStatus.ROLLED_BACK
                except Exception as e:
                    logger.error(f"Compensation failed for '{step.name}': {e}")


# =============================================================================
# CQRS MEDIATOR
# =============================================================================

class CQRSMediator:
    """
    Master CQRS mediator for BAEL.

    Provides unified access to command, query, and event buses.
    """

    def __init__(self):
        self.command_bus = CommandBus()
        self.query_bus = QueryBus()
        self.event_bus = EventBus()

        # Middleware
        self.audit_middleware = AuditMiddleware()
        self.validation_middleware = ValidationMiddleware()

        # Setup default middleware
        self.command_bus.use(LoggingMiddleware())
        self.command_bus.use(self.audit_middleware)
        self.command_bus.use(self.validation_middleware)

    # Command methods
    def register_command(
        self,
        command_type: Type[TCommand],
        handler: Union[CommandHandler, Callable]
    ) -> None:
        """Register command handler."""
        self.command_bus.register(command_type, handler)

    def command_handler(
        self,
        command_type: Type[TCommand]
    ) -> Callable:
        """Decorator for command handlers."""
        return self.command_bus.handler(command_type)

    async def send(
        self,
        command: Command,
        user_id: str = None
    ) -> CommandResult:
        """Send a command."""
        result = await self.command_bus.dispatch(command, user_id)

        # Publish events from result
        if result.events:
            await self.event_bus.publish_many(result.events)

        return result

    # Query methods
    def register_query(
        self,
        query_type: Type[TQuery],
        handler: Union[QueryHandler, Callable]
    ) -> None:
        """Register query handler."""
        self.query_bus.register(query_type, handler)

    def query_handler(
        self,
        query_type: Type[TQuery]
    ) -> Callable:
        """Decorator for query handlers."""
        return self.query_bus.handler(query_type)

    async def query(
        self,
        query: Query,
        use_cache: bool = False
    ) -> QueryResult:
        """Execute a query."""
        return await self.query_bus.query(query, use_cache)

    # Event methods
    def subscribe(
        self,
        event_type: Type[Event],
        handler: Union[EventHandler, Callable]
    ) -> None:
        """Subscribe to events."""
        self.event_bus.subscribe(event_type, handler)

    async def publish(self, event: Event) -> None:
        """Publish an event."""
        await self.event_bus.publish(event)

    # Saga methods
    def create_saga(self) -> Saga:
        """Create a new saga."""
        return Saga()

    # Validation
    def add_validator(
        self,
        command_type: Type[Command],
        validator: Callable[[Command], bool]
    ) -> None:
        """Add command validator."""
        self.validation_middleware.register_validator(command_type, validator)

    # Middleware
    def add_middleware(self, middleware: Middleware) -> None:
        """Add command middleware."""
        self.command_bus.use(middleware)

    # Audit
    def get_audit_log(
        self,
        user_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get audit log."""
        return self.audit_middleware.get_audit_log(user_id=user_id, limit=limit)

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get CQRS statistics."""
        return {
            "commands": {
                "handlers": len(self.command_bus.handlers),
                "executions": self.command_bus.execution_count,
                "errors": self.command_bus.error_count
            },
            "queries": {
                "handlers": len(self.query_bus.handlers),
                "executions": self.query_bus.execution_count
            },
            "events": {
                "handlers": sum(len(h) for h in self.event_bus.handlers.values()),
                "published": self.event_bus.publish_count
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Command Bus & CQRS System."""
    print("=" * 70)
    print("BAEL - COMMAND BUS & CQRS SYSTEM DEMO")
    print("Command Query Responsibility Segregation")
    print("=" * 70)
    print()

    mediator = CQRSMediator()

    # Define commands, queries, and events
    @dataclass
    class CreateUserCommand(Command):
        username: str = ""
        email: str = ""

    @dataclass
    class UpdateUserCommand(Command):
        user_id: str = ""
        email: str = ""

    @dataclass
    class GetUserQuery(Query):
        user_id: str = ""

    @dataclass
    class ListUsersQuery(Query):
        limit: int = 10

    @dataclass
    class UserCreatedEvent(Event):
        user_id: str = ""
        username: str = ""

    # In-memory storage
    users: Dict[str, Dict] = {}
    events_received: List[Event] = []

    # 1. Register Command Handlers
    print("1. REGISTERING HANDLERS:")
    print("-" * 40)

    @mediator.command_handler(CreateUserCommand)
    async def handle_create_user(cmd: CreateUserCommand, ctx: CommandContext):
        user_id = str(uuid.uuid4())[:8]
        users[user_id] = {
            "id": user_id,
            "username": cmd.username,
            "email": cmd.email,
            "created_by": ctx.user_id
        }
        return {"user_id": user_id}

    @mediator.command_handler(UpdateUserCommand)
    async def handle_update_user(cmd: UpdateUserCommand, ctx: CommandContext):
        if cmd.user_id not in users:
            raise ValueError(f"User {cmd.user_id} not found")
        users[cmd.user_id]["email"] = cmd.email
        return {"updated": True}

    @mediator.query_handler(GetUserQuery)
    async def handle_get_user(query: GetUserQuery):
        return users.get(query.user_id)

    @mediator.query_handler(ListUsersQuery)
    async def handle_list_users(query: ListUsersQuery):
        return list(users.values())[:query.limit]

    print("   ✓ CreateUserCommand handler registered")
    print("   ✓ UpdateUserCommand handler registered")
    print("   ✓ GetUserQuery handler registered")
    print("   ✓ ListUsersQuery handler registered")
    print()

    # 2. Event Subscription
    print("2. EVENT SUBSCRIPTION:")
    print("-" * 40)

    mediator.subscribe(UserCreatedEvent, lambda e: events_received.append(e))
    print("   ✓ Subscribed to UserCreatedEvent")
    print()

    # 3. Send Commands
    print("3. SENDING COMMANDS:")
    print("-" * 40)

    result1 = await mediator.send(
        CreateUserCommand(username="john_doe", email="john@example.com"),
        user_id="admin"
    )
    print(f"   Create user result: {result1.data}")
    print(f"   Status: {result1.status.value}")
    print(f"   Execution time: {result1.execution_time_ms:.2f}ms")

    user_id = result1.data["user_id"]

    result2 = await mediator.send(
        CreateUserCommand(username="jane_doe", email="jane@example.com"),
        user_id="admin"
    )
    print(f"   Create second user: {result2.data}")
    print()

    # 4. Execute Queries
    print("4. EXECUTING QUERIES:")
    print("-" * 40)

    query_result = await mediator.query(GetUserQuery(user_id=user_id))
    print(f"   Get user result: {query_result.data}")
    print(f"   Execution time: {query_result.execution_time_ms:.2f}ms")

    list_result = await mediator.query(ListUsersQuery(limit=10))
    print(f"   List users count: {len(list_result.data)}")
    print()

    # 5. Query Caching
    print("5. QUERY CACHING:")
    print("-" * 40)

    result_nocache = await mediator.query(GetUserQuery(user_id=user_id))
    print(f"   Without cache - from_cache: {result_nocache.from_cache}")

    result_cached = await mediator.query(GetUserQuery(user_id=user_id), use_cache=True)
    print(f"   With cache (1st) - from_cache: {result_cached.from_cache}")

    result_cached2 = await mediator.query(GetUserQuery(user_id=user_id), use_cache=True)
    print(f"   With cache (2nd) - from_cache: {result_cached2.from_cache}")
    print()

    # 6. Event Publishing
    print("6. EVENT PUBLISHING:")
    print("-" * 40)

    await mediator.publish(UserCreatedEvent(user_id=user_id, username="john_doe"))
    print(f"   Events received: {len(events_received)}")
    print(f"   Latest event: {events_received[-1].event_name}")
    print()

    # 7. Command Validation
    print("7. COMMAND VALIDATION:")
    print("-" * 40)

    def validate_create_user(cmd: CreateUserCommand) -> bool:
        return len(cmd.username) >= 3 and "@" in cmd.email

    mediator.add_validator(CreateUserCommand, validate_create_user)

    invalid_result = await mediator.send(
        CreateUserCommand(username="ab", email="invalid"),
        user_id="admin"
    )
    print(f"   Invalid command status: {invalid_result.status.value}")
    print(f"   Error: {invalid_result.error}")
    print()

    # 8. Saga Orchestration
    print("8. SAGA ORCHESTRATION:")
    print("-" * 40)

    saga_operations: List[str] = []

    saga = mediator.create_saga()

    saga.add_step(
        name="Create Order",
        execute=lambda: saga_operations.append("order_created") or "order-123",
        compensate=lambda: saga_operations.append("order_cancelled") or None
    )

    saga.add_step(
        name="Reserve Inventory",
        execute=lambda: saga_operations.append("inventory_reserved") or True,
        compensate=lambda: saga_operations.append("inventory_released") or None
    )

    saga.add_step(
        name="Process Payment",
        execute=lambda: saga_operations.append("payment_processed") or True,
        compensate=lambda: saga_operations.append("payment_refunded") or None
    )

    success = await saga.execute()
    print(f"   Saga success: {success}")
    print(f"   Saga status: {saga.status.value}")
    print(f"   Operations: {saga_operations}")
    print()

    # 9. Saga with Compensation
    print("9. SAGA WITH COMPENSATION:")
    print("-" * 40)

    comp_operations: List[str] = []

    failing_saga = Saga()

    failing_saga.add_step(
        name="Step 1",
        execute=lambda: comp_operations.append("step1_done") or True,
        compensate=lambda: comp_operations.append("step1_compensated") or None
    )

    failing_saga.add_step(
        name="Step 2",
        execute=lambda: comp_operations.append("step2_done") or True,
        compensate=lambda: comp_operations.append("step2_compensated") or None
    )

    async def failing_step():
        comp_operations.append("step3_failed")
        raise ValueError("Simulated failure")

    failing_saga.add_step(
        name="Step 3 (fails)",
        execute=failing_step,
        compensate=lambda: comp_operations.append("step3_compensated") or None
    )

    result = await failing_saga.execute()
    print(f"   Saga success: {result}")
    print(f"   Saga status: {failing_saga.status.value}")
    print(f"   Operations: {comp_operations}")
    print()

    # 10. Audit Log
    print("10. AUDIT LOG:")
    print("-" * 40)

    audit = mediator.get_audit_log(limit=5)
    for entry in audit:
        print(f"    - {entry['command_name']}: {entry['status']}")
    print()

    # 11. Statistics
    print("11. CQRS STATISTICS:")
    print("-" * 40)

    stats = mediator.get_statistics()
    print(f"    Commands:")
    print(f"      Handlers: {stats['commands']['handlers']}")
    print(f"      Executions: {stats['commands']['executions']}")
    print(f"      Errors: {stats['commands']['errors']}")
    print(f"    Queries:")
    print(f"      Handlers: {stats['queries']['handlers']}")
    print(f"      Executions: {stats['queries']['executions']}")
    print(f"    Events:")
    print(f"      Handlers: {stats['events']['handlers']}")
    print(f"      Published: {stats['events']['published']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - CQRS System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
