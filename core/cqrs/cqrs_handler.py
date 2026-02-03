#!/usr/bin/env python3
"""
BAEL - CQRS Handler
Command Query Responsibility Segregation system.

Features:
- Command handling
- Query handling
- Event publishing
- Read/write separation
- Command validation
- Query caching
- Middleware support
- Async execution
- Pipeline pattern
- Command bus
"""

import asyncio
import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
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

class ExecutionStatus(Enum):
    """Command/Query execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationResult(Enum):
    """Validation result."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# =============================================================================
# BASE CLASSES
# =============================================================================

@dataclass
class Command:
    """Base class for commands."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_name(self) -> str:
        return self.__class__.__name__


@dataclass
class Query(Generic[TResult]):
    """Base class for queries."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def query_name(self) -> str:
        return self.__class__.__name__


@dataclass
class CommandResult:
    """Result of command execution."""
    command_id: str
    success: bool
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    data: Any = None
    error: Optional[str] = None
    events: List[Any] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class QueryResult(Generic[TResult]):
    """Result of query execution."""
    query_id: str
    success: bool
    data: Optional[TResult] = None
    error: Optional[str] = None
    from_cache: bool = False
    execution_time: float = 0.0


# =============================================================================
# HANDLERS
# =============================================================================

class CommandHandler(ABC, Generic[TCommand]):
    """Abstract command handler."""

    @abstractmethod
    async def handle(self, command: TCommand) -> CommandResult:
        """Handle the command."""
        pass

    async def validate(self, command: TCommand) -> List[str]:
        """Validate command. Returns list of errors."""
        return []


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Abstract query handler."""

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle the query."""
        pass


# =============================================================================
# VALIDATORS
# =============================================================================

class CommandValidator(ABC, Generic[TCommand]):
    """Abstract command validator."""

    @abstractmethod
    async def validate(self, command: TCommand) -> Tuple[ValidationResult, List[str]]:
        """Validate command."""
        pass


class CompositeValidator(CommandValidator[TCommand]):
    """Composite of multiple validators."""

    def __init__(self, validators: List[CommandValidator[TCommand]]):
        self.validators = validators

    async def validate(self, command: TCommand) -> Tuple[ValidationResult, List[str]]:
        all_errors = []
        has_warning = False

        for validator in self.validators:
            result, errors = await validator.validate(command)

            if result == ValidationResult.INVALID:
                all_errors.extend(errors)
            elif result == ValidationResult.WARNING:
                has_warning = True
                all_errors.extend(errors)

        if all_errors and not has_warning:
            return ValidationResult.INVALID, all_errors
        elif has_warning:
            return ValidationResult.WARNING, all_errors

        return ValidationResult.VALID, []


# =============================================================================
# MIDDLEWARE
# =============================================================================

class CommandMiddleware(ABC):
    """Middleware for command processing."""

    @abstractmethod
    async def process(
        self,
        command: Command,
        next_handler: Callable[[Command], Awaitable[CommandResult]]
    ) -> CommandResult:
        """Process command through middleware."""
        pass


class LoggingMiddleware(CommandMiddleware):
    """Logging middleware."""

    async def process(
        self,
        command: Command,
        next_handler: Callable[[Command], Awaitable[CommandResult]]
    ) -> CommandResult:
        logger.info(f"Executing command: {command.command_name}")

        try:
            result = await next_handler(command)

            if result.success:
                logger.info(f"Command completed: {command.command_name}")
            else:
                logger.warning(f"Command failed: {command.command_name} - {result.error}")

            return result

        except Exception as e:
            logger.exception(f"Command error: {command.command_name}")
            raise


class TimingMiddleware(CommandMiddleware):
    """Timing middleware."""

    async def process(
        self,
        command: Command,
        next_handler: Callable[[Command], Awaitable[CommandResult]]
    ) -> CommandResult:
        start = time.time()

        result = await next_handler(command)

        result.execution_time = time.time() - start

        return result


class ValidationMiddleware(CommandMiddleware):
    """Validation middleware."""

    def __init__(self, validators: Dict[Type[Command], CommandValidator] = None):
        self.validators = validators or {}

    def register_validator(
        self,
        command_type: Type[Command],
        validator: CommandValidator
    ) -> None:
        self.validators[command_type] = validator

    async def process(
        self,
        command: Command,
        next_handler: Callable[[Command], Awaitable[CommandResult]]
    ) -> CommandResult:
        validator = self.validators.get(type(command))

        if validator:
            result, errors = await validator.validate(command)

            if result == ValidationResult.INVALID:
                return CommandResult(
                    command_id=command.command_id,
                    success=False,
                    status=ExecutionStatus.FAILED,
                    error=f"Validation failed: {', '.join(errors)}"
                )

        return await next_handler(command)


# =============================================================================
# QUERY CACHE
# =============================================================================

class QueryCache:
    """Cache for query results."""

    def __init__(self, default_ttl: int = 60):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl

    def _get_key(self, query: Query) -> str:
        """Generate cache key for query."""
        # Create deterministic key from query attributes
        key_data = f"{query.query_name}:{hash(frozenset(query.__dict__.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, query: Query) -> Optional[Any]:
        """Get cached result."""
        key = self._get_key(query)

        if key in self._cache:
            result, expires = self._cache[key]

            if datetime.utcnow() < expires:
                return result
            else:
                del self._cache[key]

        return None

    def set(self, query: Query, result: Any, ttl: Optional[int] = None) -> None:
        """Cache query result."""
        key = self._get_key(query)
        expires = datetime.utcnow() + timedelta(seconds=ttl or self._default_ttl)
        self._cache[key] = (result, expires)

    def invalidate(self, query: Query) -> None:
        """Invalidate cached result."""
        key = self._get_key(query)
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()


# =============================================================================
# EVENT PUBLISHER
# =============================================================================

class EventPublisher:
    """Publish domain events."""

    def __init__(self):
        self._handlers: Dict[Type, List[Callable]] = {}
        self._pending: List[Any] = []

    def subscribe(
        self,
        event_type: Type[T],
        handler: Callable[[T], Awaitable[None]]
    ) -> None:
        """Subscribe to event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        """Publish event to handlers."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def publish_all(self, events: List[Any]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)

    def queue(self, event: Any) -> None:
        """Queue event for later publishing."""
        self._pending.append(event)

    async def flush(self) -> None:
        """Publish all queued events."""
        events = self._pending.copy()
        self._pending.clear()
        await self.publish_all(events)


# =============================================================================
# CQRS HANDLER
# =============================================================================

class CQRSHandler:
    """
    CQRS Handler for BAEL.

    Implements Command Query Responsibility Segregation.
    """

    def __init__(self):
        self._command_handlers: Dict[Type[Command], CommandHandler] = {}
        self._query_handlers: Dict[Type[Query], QueryHandler] = {}
        self._middleware: List[CommandMiddleware] = []
        self._query_cache = QueryCache()
        self._event_publisher = EventPublisher()
        self._cache_config: Dict[Type[Query], int] = {}  # query type -> ttl

    # -------------------------------------------------------------------------
    # HANDLER REGISTRATION
    # -------------------------------------------------------------------------

    def register_command_handler(
        self,
        command_type: Type[TCommand],
        handler: CommandHandler[TCommand]
    ) -> None:
        """Register command handler."""
        self._command_handlers[command_type] = handler

    def register_query_handler(
        self,
        query_type: Type[TQuery],
        handler: QueryHandler[TQuery, TResult]
    ) -> None:
        """Register query handler."""
        self._query_handlers[query_type] = handler

    def command_handler(self, command_type: Type[TCommand]):
        """Decorator to register command handler."""
        def decorator(handler_class: Type[CommandHandler[TCommand]]):
            self.register_command_handler(command_type, handler_class())
            return handler_class
        return decorator

    def query_handler(self, query_type: Type[TQuery]):
        """Decorator to register query handler."""
        def decorator(handler_class: Type[QueryHandler[TQuery, TResult]]):
            self.register_query_handler(query_type, handler_class())
            return handler_class
        return decorator

    # -------------------------------------------------------------------------
    # MIDDLEWARE
    # -------------------------------------------------------------------------

    def use_middleware(self, middleware: CommandMiddleware) -> None:
        """Add command middleware."""
        self._middleware.append(middleware)

    def use_logging(self) -> None:
        """Add logging middleware."""
        self.use_middleware(LoggingMiddleware())

    def use_timing(self) -> None:
        """Add timing middleware."""
        self.use_middleware(TimingMiddleware())

    # -------------------------------------------------------------------------
    # COMMAND EXECUTION
    # -------------------------------------------------------------------------

    async def send(self, command: Command) -> CommandResult:
        """Send a command for execution."""
        handler = self._command_handlers.get(type(command))

        if not handler:
            return CommandResult(
                command_id=command.command_id,
                success=False,
                status=ExecutionStatus.FAILED,
                error=f"No handler for command: {command.command_name}"
            )

        # Build middleware chain
        async def execute(cmd: Command) -> CommandResult:
            try:
                # Validate
                errors = await handler.validate(cmd)
                if errors:
                    return CommandResult(
                        command_id=cmd.command_id,
                        success=False,
                        status=ExecutionStatus.FAILED,
                        error=f"Validation failed: {', '.join(errors)}"
                    )

                # Execute
                result = await handler.handle(cmd)

                # Publish events
                if result.events:
                    await self._event_publisher.publish_all(result.events)

                return result

            except Exception as e:
                return CommandResult(
                    command_id=cmd.command_id,
                    success=False,
                    status=ExecutionStatus.FAILED,
                    error=str(e)
                )

        # Apply middleware
        chain = execute
        for middleware in reversed(self._middleware):
            chain = self._wrap_middleware(middleware, chain)

        return await chain(command)

    def _wrap_middleware(
        self,
        middleware: CommandMiddleware,
        next_handler: Callable[[Command], Awaitable[CommandResult]]
    ) -> Callable[[Command], Awaitable[CommandResult]]:
        """Wrap middleware for chain execution."""
        async def wrapped(command: Command) -> CommandResult:
            return await middleware.process(command, next_handler)
        return wrapped

    # -------------------------------------------------------------------------
    # QUERY EXECUTION
    # -------------------------------------------------------------------------

    async def query(
        self,
        query: Query[TResult],
        use_cache: bool = True
    ) -> QueryResult[TResult]:
        """Execute a query."""
        start = time.time()

        handler = self._query_handlers.get(type(query))

        if not handler:
            return QueryResult(
                query_id=query.query_id,
                success=False,
                error=f"No handler for query: {query.query_name}"
            )

        # Check cache
        if use_cache and type(query) in self._cache_config:
            cached = self._query_cache.get(query)
            if cached is not None:
                return QueryResult(
                    query_id=query.query_id,
                    success=True,
                    data=cached,
                    from_cache=True,
                    execution_time=time.time() - start
                )

        try:
            result = await handler.handle(query)

            # Cache result
            if use_cache and type(query) in self._cache_config:
                ttl = self._cache_config[type(query)]
                self._query_cache.set(query, result, ttl)

            return QueryResult(
                query_id=query.query_id,
                success=True,
                data=result,
                execution_time=time.time() - start
            )

        except Exception as e:
            return QueryResult(
                query_id=query.query_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start
            )

    # -------------------------------------------------------------------------
    # CACHE CONFIGURATION
    # -------------------------------------------------------------------------

    def cache_query(self, query_type: Type[Query], ttl: int = 60) -> None:
        """Configure caching for a query type."""
        self._cache_config[query_type] = ttl

    def invalidate_cache(self, query: Query) -> None:
        """Invalidate cache for a query."""
        self._query_cache.invalidate(query)

    def clear_cache(self) -> None:
        """Clear all query cache."""
        self._query_cache.clear()

    # -------------------------------------------------------------------------
    # EVENT SUBSCRIPTIONS
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        event_type: Type[T],
        handler: Callable[[T], Awaitable[None]]
    ) -> None:
        """Subscribe to domain events."""
        self._event_publisher.subscribe(event_type, handler)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def list_commands(self) -> List[str]:
        """List registered command types."""
        return [t.__name__ for t in self._command_handlers.keys()]

    def list_queries(self) -> List[str]:
        """List registered query types."""
        return [t.__name__ for t in self._query_handlers.keys()]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the CQRS Handler."""
    print("=" * 70)
    print("BAEL - CQRS HANDLER DEMO")
    print("Command Query Responsibility Segregation")
    print("=" * 70)
    print()

    cqrs = CQRSHandler()
    cqrs.use_logging()
    cqrs.use_timing()

    # 1. Define Commands
    print("1. DEFINE COMMANDS:")
    print("-" * 40)

    @dataclass
    class CreateUser(Command):
        username: str = ""
        email: str = ""

    @dataclass
    class UpdateUser(Command):
        user_id: str = ""
        email: str = ""

    @dataclass
    class DeleteUser(Command):
        user_id: str = ""

    print("   Defined: CreateUser, UpdateUser, DeleteUser")
    print()

    # 2. Define Queries
    print("2. DEFINE QUERIES:")
    print("-" * 40)

    @dataclass
    class GetUser(Query[Dict[str, Any]]):
        user_id: str = ""

    @dataclass
    class ListUsers(Query[List[Dict[str, Any]]]):
        page: int = 1
        limit: int = 10

    print("   Defined: GetUser, ListUsers")
    print()

    # 3. Define Events
    print("3. DEFINE EVENTS:")
    print("-" * 40)

    @dataclass
    class UserCreated:
        user_id: str
        username: str

    @dataclass
    class UserUpdated:
        user_id: str
        email: str

    print("   Defined: UserCreated, UserUpdated")
    print()

    # 4. Implement Handlers
    print("4. IMPLEMENT HANDLERS:")
    print("-" * 40)

    # In-memory store
    users_store: Dict[str, Dict] = {}

    class CreateUserHandler(CommandHandler[CreateUser]):
        async def validate(self, command: CreateUser) -> List[str]:
            errors = []
            if not command.username:
                errors.append("Username is required")
            if not command.email:
                errors.append("Email is required")
            return errors

        async def handle(self, command: CreateUser) -> CommandResult:
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "username": command.username,
                "email": command.email
            }
            users_store[user_id] = user

            return CommandResult(
                command_id=command.command_id,
                success=True,
                data={"user_id": user_id},
                events=[UserCreated(user_id, command.username)]
            )

    class GetUserHandler(QueryHandler[GetUser, Dict[str, Any]]):
        async def handle(self, query: GetUser) -> Dict[str, Any]:
            return users_store.get(query.user_id, {})

    class ListUsersHandler(QueryHandler[ListUsers, List[Dict[str, Any]]]):
        async def handle(self, query: ListUsers) -> List[Dict[str, Any]]:
            all_users = list(users_store.values())
            start = (query.page - 1) * query.limit
            return all_users[start:start + query.limit]

    cqrs.register_command_handler(CreateUser, CreateUserHandler())
    cqrs.register_query_handler(GetUser, GetUserHandler())
    cqrs.register_query_handler(ListUsers, ListUsersHandler())

    print("   Registered: CreateUserHandler, GetUserHandler, ListUsersHandler")
    print()

    # 5. Execute Command
    print("5. EXECUTE COMMAND:")
    print("-" * 40)

    command = CreateUser(username="john_doe", email="john@example.com")
    result = await cqrs.send(command)

    print(f"   Command: CreateUser")
    print(f"   Success: {result.success}")
    print(f"   User ID: {result.data.get('user_id', '')[:8]}...")
    print(f"   Events: {[type(e).__name__ for e in result.events]}")
    print(f"   Time: {result.execution_time:.4f}s")
    print()

    # 6. Execute Query
    print("6. EXECUTE QUERY:")
    print("-" * 40)

    user_id = result.data["user_id"]
    query = GetUser(user_id=user_id)
    query_result = await cqrs.query(query)

    print(f"   Query: GetUser")
    print(f"   Success: {query_result.success}")
    print(f"   Data: {query_result.data}")
    print()

    # 7. Command Validation
    print("7. COMMAND VALIDATION:")
    print("-" * 40)

    invalid_command = CreateUser(username="", email="")
    result = await cqrs.send(invalid_command)

    print(f"   Command: CreateUser (invalid)")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    print()

    # 8. Query Caching
    print("8. QUERY CACHING:")
    print("-" * 40)

    # Configure caching
    cqrs.cache_query(ListUsers, ttl=60)

    # First query (not cached)
    query1 = ListUsers(page=1, limit=10)
    result1 = await cqrs.query(query1)

    # Second query (cached)
    result2 = await cqrs.query(query1)

    print(f"   First query - from cache: {result1.from_cache}")
    print(f"   Second query - from cache: {result2.from_cache}")
    print()

    # 9. Event Subscriptions
    print("9. EVENT SUBSCRIPTIONS:")
    print("-" * 40)

    events_received = []

    async def on_user_created(event: UserCreated):
        events_received.append(event)

    cqrs.subscribe(UserCreated, on_user_created)

    # Create another user
    command = CreateUser(username="jane_doe", email="jane@example.com")
    await cqrs.send(command)

    print(f"   Events received: {len(events_received)}")
    print(f"   Last event: UserCreated({events_received[-1].username})")
    print()

    # 10. List Registered Handlers
    print("10. REGISTERED HANDLERS:")
    print("-" * 40)

    print(f"   Commands: {cqrs.list_commands()}")
    print(f"   Queries: {cqrs.list_queries()}")
    print()

    # 11. Multiple Commands
    print("11. MULTIPLE COMMANDS:")
    print("-" * 40)

    for i in range(3):
        cmd = CreateUser(username=f"user_{i}", email=f"user{i}@example.com")
        await cqrs.send(cmd)

    # Query all users
    query = ListUsers()
    result = await cqrs.query(query, use_cache=False)

    print(f"   Created 3 additional users")
    print(f"   Total users: {len(result.data)}")
    print()

    # 12. Query with Parameters
    print("12. QUERY WITH PARAMETERS:")
    print("-" * 40)

    page1 = await cqrs.query(ListUsers(page=1, limit=2), use_cache=False)
    page2 = await cqrs.query(ListUsers(page=2, limit=2), use_cache=False)

    print(f"   Page 1 users: {len(page1.data)}")
    print(f"   Page 2 users: {len(page2.data)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - CQRS Handler Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
