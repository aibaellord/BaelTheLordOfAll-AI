"""
BAEL CQRS Engine Implementation
================================

Command Query Responsibility Segregation for clean architecture.

"Ba'el commands with authority and queries with wisdom." — Ba'el
"""

import asyncio
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.CQRS")

T = TypeVar('T')
TResult = TypeVar('TResult')


# ============================================================================
# ENUMS
# ============================================================================

class CommandStatus(Enum):
    """Command execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATED = "compensated"


class QueryType(Enum):
    """Query types."""
    SINGLE = "single"      # Get one item
    LIST = "list"          # Get multiple items
    PAGED = "paged"        # Paginated results
    COUNT = "count"        # Count only
    EXISTS = "exists"      # Existence check
    AGGREGATE = "aggregate"  # Aggregated data


# ============================================================================
# COMMANDS
# ============================================================================

@dataclass
class Command:
    """
    Base command.

    Commands are intentions to change state.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    # Auth
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Data
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Command name (class name)."""
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'causation_id': self.causation_id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'data': self.data
        }


@dataclass
class CommandResult:
    """Result of command execution."""
    command_id: str
    status: CommandStatus

    # Result data
    data: Any = None
    aggregate_id: Optional[str] = None
    events: List[Any] = field(default_factory=list)

    # Error info
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == CommandStatus.SUCCEEDED

    @classmethod
    def success_result(
        cls,
        command_id: str,
        data: Any = None,
        **kwargs
    ) -> 'CommandResult':
        """Create success result."""
        return cls(
            command_id=command_id,
            status=CommandStatus.SUCCEEDED,
            data=data,
            **kwargs
        )

    @classmethod
    def failure_result(
        cls,
        command_id: str,
        error: str,
        error_code: Optional[str] = None
    ) -> 'CommandResult':
        """Create failure result."""
        return cls(
            command_id=command_id,
            status=CommandStatus.FAILED,
            error=error,
            error_code=error_code
        )


# ============================================================================
# QUERIES
# ============================================================================

@dataclass
class Query:
    """
    Base query.

    Queries are requests for data that don't modify state.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Type
    query_type: QueryType = QueryType.SINGLE

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)

    # Auth
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Pagination
    page: int = 1
    page_size: int = 20

    # Filtering & sorting
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: Optional[str] = None
    sort_desc: bool = False

    @property
    def name(self) -> str:
        """Query name (class name)."""
        return self.__class__.__name__

    @property
    def offset(self) -> int:
        """Calculate offset for pagination."""
        return (self.page - 1) * self.page_size


@dataclass
class QueryResult(Generic[T]):
    """Result of query execution."""
    query_id: str

    # Result data
    data: Optional[T] = None
    items: List[T] = field(default_factory=list)

    # Pagination
    total: int = 0
    page: int = 1
    page_size: int = 20

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0

    # Cache
    from_cache: bool = False

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page * self.page_size < self.total

    @property
    def total_pages(self) -> int:
        """Get total page count."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


# ============================================================================
# HANDLERS
# ============================================================================

class CommandHandler(ABC, Generic[T]):
    """
    Base command handler.

    Override handle() to implement command logic.
    """

    @abstractmethod
    async def handle(self, command: T) -> CommandResult:
        """Handle the command."""
        pass

    def can_handle(self, command: Command) -> bool:
        """Check if this handler can handle the command."""
        return True

    async def validate(self, command: T) -> Optional[str]:
        """Validate command. Return error message if invalid."""
        return None


class QueryHandler(ABC, Generic[T, TResult]):
    """
    Base query handler.

    Override handle() to implement query logic.
    """

    @abstractmethod
    async def handle(self, query: T) -> QueryResult[TResult]:
        """Handle the query."""
        pass

    def can_handle(self, query: Query) -> bool:
        """Check if this handler can handle the query."""
        return True


# ============================================================================
# COMMAND BUS
# ============================================================================

class CommandBus:
    """
    Command bus for routing commands to handlers.

    Features:
    - Command routing
    - Middleware pipeline
    - Validation
    - Logging
    """

    def __init__(self):
        # Handlers: command_type -> handler
        self._handlers: Dict[Type, CommandHandler] = {}

        # Middleware: list of functions
        self._middleware: List[Callable] = []

        self._lock = threading.RLock()

        logger.info("Command bus initialized")

    def register(
        self,
        command_type: Type[T],
        handler: CommandHandler[T]
    ) -> None:
        """Register command handler."""
        with self._lock:
            self._handlers[command_type] = handler

        logger.debug(f"Registered handler for {command_type.__name__}")

    def register_handler(self, handler: CommandHandler) -> Callable:
        """Decorator to register handler for command type."""
        def decorator(command_type: Type[T]) -> Type[T]:
            self.register(command_type, handler)
            return command_type
        return decorator

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to pipeline."""
        with self._lock:
            self._middleware.append(middleware)

    async def dispatch(self, command: Command) -> CommandResult:
        """Dispatch command to handler."""
        start_time = datetime.now()

        try:
            command_type = type(command)
            handler = self._handlers.get(command_type)

            if not handler:
                return CommandResult.failure_result(
                    command.id,
                    f"No handler for command: {command_type.__name__}",
                    "HANDLER_NOT_FOUND"
                )

            if not handler.can_handle(command):
                return CommandResult.failure_result(
                    command.id,
                    "Handler cannot process this command",
                    "HANDLER_REJECTED"
                )

            # Validate
            validation_error = await handler.validate(command)
            if validation_error:
                return CommandResult.failure_result(
                    command.id,
                    validation_error,
                    "VALIDATION_ERROR"
                )

            # Apply middleware
            for middleware in self._middleware:
                command = await middleware(command)

            # Execute
            result = await handler.handle(command)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            result.duration_ms = duration

            logger.debug(
                f"Command {command.name} executed in {duration:.2f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult.failure_result(
                command.id,
                str(e),
                "EXECUTION_ERROR"
            )

    def dispatch_sync(self, command: Command) -> CommandResult:
        """Dispatch synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.dispatch(command))
        finally:
            loop.close()

    def get_status(self) -> Dict[str, Any]:
        """Get bus status."""
        with self._lock:
            return {
                'handlers': len(self._handlers),
                'middleware': len(self._middleware),
                'commands': [t.__name__ for t in self._handlers.keys()]
            }


# ============================================================================
# QUERY BUS
# ============================================================================

class QueryBus:
    """
    Query bus for routing queries to handlers.

    Features:
    - Query routing
    - Caching
    - Middleware
    """

    def __init__(self):
        # Handlers: query_type -> handler
        self._handlers: Dict[Type, QueryHandler] = {}

        # Cache: query_key -> (result, expiry)
        self._cache: Dict[str, tuple] = {}

        # Middleware
        self._middleware: List[Callable] = []

        self._lock = threading.RLock()

        logger.info("Query bus initialized")

    def register(
        self,
        query_type: Type[T],
        handler: QueryHandler[T, TResult]
    ) -> None:
        """Register query handler."""
        with self._lock:
            self._handlers[query_type] = handler

        logger.debug(f"Registered handler for {query_type.__name__}")

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to pipeline."""
        with self._lock:
            self._middleware.append(middleware)

    async def dispatch(
        self,
        query: Query,
        use_cache: bool = True,
        cache_ttl: int = 60
    ) -> QueryResult:
        """Dispatch query to handler."""
        start_time = datetime.now()

        try:
            query_type = type(query)
            handler = self._handlers.get(query_type)

            if not handler:
                return QueryResult(
                    query_id=query.id,
                    data=None
                )

            if not handler.can_handle(query):
                return QueryResult(
                    query_id=query.id,
                    data=None
                )

            # Check cache
            if use_cache:
                cache_key = self._get_cache_key(query)
                cached = self._get_cached(cache_key)
                if cached:
                    cached.from_cache = True
                    return cached

            # Apply middleware
            for middleware in self._middleware:
                query = await middleware(query)

            # Execute
            result = await handler.handle(query)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            result.duration_ms = duration

            # Cache result
            if use_cache:
                self._set_cached(cache_key, result, cache_ttl)

            logger.debug(
                f"Query {query.name} executed in {duration:.2f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(query_id=query.id, data=None)

    def dispatch_sync(self, query: Query, **kwargs) -> QueryResult:
        """Dispatch synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.dispatch(query, **kwargs))
        finally:
            loop.close()

    def _get_cache_key(self, query: Query) -> str:
        """Generate cache key for query."""
        import hashlib
        import json

        data = {
            'type': type(query).__name__,
            'filters': query.filters,
            'page': query.page,
            'page_size': query.page_size,
            'sort_by': query.sort_by,
            'sort_desc': query.sort_desc
        }

        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[QueryResult]:
        """Get cached result."""
        with self._lock:
            if key in self._cache:
                result, expiry = self._cache[key]
                if datetime.now() < expiry:
                    return result
                del self._cache[key]
        return None

    def _set_cached(
        self,
        key: str,
        result: QueryResult,
        ttl: int
    ) -> None:
        """Cache a result."""
        from datetime import timedelta

        with self._lock:
            expiry = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (result, expiry)

    def clear_cache(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get bus status."""
        with self._lock:
            return {
                'handlers': len(self._handlers),
                'middleware': len(self._middleware),
                'cached': len(self._cache),
                'queries': [t.__name__ for t in self._handlers.keys()]
            }


# ============================================================================
# CQRS ENGINE
# ============================================================================

class CQRSEngine:
    """
    High-level CQRS engine.

    Combines command and query buses with additional features.

    "Ba'el unifies command and query for transcendent architecture." — Ba'el
    """

    def __init__(
        self,
        command_bus: Optional[CommandBus] = None,
        query_bus: Optional[QueryBus] = None
    ):
        """Initialize engine."""
        self.commands = command_bus or CommandBus()
        self.queries = query_bus or QueryBus()

        # Command log
        self._command_log: List[Command] = []
        self._log_enabled = False

        logger.info("CQRS Engine initialized")

    def enable_logging(self, enabled: bool = True) -> None:
        """Enable command logging."""
        self._log_enabled = enabled

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command."""
        if self._log_enabled:
            self._command_log.append(command)

        return await self.commands.dispatch(command)

    async def query(
        self,
        query: Query,
        use_cache: bool = True
    ) -> QueryResult:
        """Execute a query."""
        return await self.queries.dispatch(query, use_cache=use_cache)

    def execute_sync(self, command: Command) -> CommandResult:
        """Execute command synchronously."""
        return self.commands.dispatch_sync(command)

    def query_sync(self, query: Query, **kwargs) -> QueryResult:
        """Execute query synchronously."""
        return self.queries.dispatch_sync(query, **kwargs)

    def get_command_log(self) -> List[Command]:
        """Get command log."""
        return self._command_log.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'commands': self.commands.get_status(),
            'queries': self.queries.get_status(),
            'log_enabled': self._log_enabled,
            'logged_commands': len(self._command_log)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

command_bus = CommandBus()
query_bus = QueryBus()
cqrs_engine = CQRSEngine(command_bus, query_bus)
