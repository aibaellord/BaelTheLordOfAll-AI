"""
BAEL Connection Pool Engine Implementation
============================================

Efficient connection resource management.

"Ba'el manages resources with divine efficiency." — Ba'el
"""

import asyncio
import logging
import threading
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.ConnectionPool")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class ConnectionState(Enum):
    """Connection states."""
    IDLE = "idle"
    IN_USE = "in_use"
    CLOSED = "closed"
    INVALID = "invalid"


class PoolState(Enum):
    """Pool states."""
    STARTING = "starting"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"


class SelectionStrategy(Enum):
    """Connection selection strategies."""
    FIFO = "fifo"          # First in, first out
    LIFO = "lifo"          # Last in, first out (keeps connections warm)
    ROUND_ROBIN = "round_robin"  # Rotate through connections


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PooledConnection(Generic[T]):
    """A pooled connection wrapper."""
    id: str
    connection: T

    # State
    state: ConnectionState = ConnectionState.IDLE

    # Tracking
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0

    # Health
    healthy: bool = True
    last_health_check: Optional[float] = None

    def is_expired(self, max_age: float) -> bool:
        """Check if connection has expired."""
        return (time.time() - self.created_at) > max_age

    def is_idle_too_long(self, max_idle: float) -> bool:
        """Check if connection has been idle too long."""
        return (time.time() - self.last_used) > max_idle


@dataclass
class PoolConfig:
    """Connection pool configuration."""
    min_size: int = 1
    max_size: int = 10
    max_idle_time_seconds: float = 300.0  # 5 minutes
    max_connection_age_seconds: float = 3600.0  # 1 hour
    acquire_timeout_seconds: float = 30.0
    validation_interval_seconds: float = 60.0
    selection_strategy: SelectionStrategy = SelectionStrategy.LIFO


@dataclass
class PoolStats:
    """Pool statistics."""
    current_size: int = 0
    idle_count: int = 0
    in_use_count: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    failed_acquires: int = 0
    timeouts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_size': self.current_size,
            'idle': self.idle_count,
            'in_use': self.in_use_count,
            'created': self.total_connections_created,
            'closed': self.total_connections_closed,
            'acquires': self.total_acquires,
            'releases': self.total_releases,
            'failed': self.failed_acquires,
            'timeouts': self.timeouts
        }


# ============================================================================
# CONNECTION POOL
# ============================================================================

class ConnectionPool(Generic[T]):
    """
    Generic connection pool.

    Features:
    - Configurable pool size
    - Connection lifecycle management
    - Health checking
    - Multiple selection strategies

    "Ba'el optimizes the flow of resources." — Ba'el
    """

    def __init__(
        self,
        factory: Callable[[], T],
        config: Optional[PoolConfig] = None,
        validator: Optional[Callable[[T], bool]] = None,
        cleanup: Optional[Callable[[T], None]] = None
    ):
        """
        Initialize connection pool.

        Args:
            factory: Function to create new connections
            config: Pool configuration
            validator: Function to validate connections
            cleanup: Function to cleanup connections
        """
        self._factory = factory
        self.config = config or PoolConfig()
        self._validator = validator
        self._cleanup = cleanup

        # Pool state
        self._state = PoolState.STARTING

        # Connections
        self._connections: Dict[str, PooledConnection[T]] = {}
        self._idle: deque = deque()
        self._waiting: deque = deque()

        # Round robin index
        self._rr_index = 0

        # Statistics
        self._stats = PoolStats()

        # Synchronization
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        # Async support
        self._async_lock: Optional[asyncio.Lock] = None
        self._async_condition: Optional[asyncio.Condition] = None

        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None

        logger.info(
            f"Connection pool initialized: "
            f"min={self.config.min_size}, max={self.config.max_size}"
        )

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def start(self) -> None:
        """Start the pool and create minimum connections."""
        with self._lock:
            self._state = PoolState.RUNNING

            # Create minimum connections
            for _ in range(self.config.min_size):
                self._create_connection()

    async def start_async(self) -> None:
        """Start pool asynchronously."""
        self._async_lock = asyncio.Lock()
        self._async_condition = asyncio.Condition(self._async_lock)

        self._state = PoolState.RUNNING

        # Create minimum connections
        for _ in range(self.config.min_size):
            await self._create_connection_async()

        # Start maintenance
        self._maintenance_task = asyncio.create_task(
            self._maintenance_loop()
        )

    def stop(self, timeout: float = 30.0) -> None:
        """Stop the pool and close all connections."""
        with self._lock:
            self._state = PoolState.DRAINING

            # Wait for in-use connections
            deadline = time.time() + timeout
            while self._stats.in_use_count > 0 and time.time() < deadline:
                self._condition.wait(timeout=1.0)

            # Close all connections
            for conn in list(self._connections.values()):
                self._close_connection(conn)

            self._state = PoolState.STOPPED

    async def stop_async(self) -> None:
        """Stop pool asynchronously."""
        if self._maintenance_task:
            self._maintenance_task.cancel()

        self._state = PoolState.DRAINING

        # Close all connections
        for conn in list(self._connections.values()):
            await self._close_connection_async(conn)

        self._state = PoolState.STOPPED

    # ========================================================================
    # CONNECTION CREATION/DESTRUCTION
    # ========================================================================

    def _create_connection(self) -> Optional[PooledConnection[T]]:
        """Create a new connection."""
        if len(self._connections) >= self.config.max_size:
            return None

        try:
            raw_conn = self._factory()

            conn = PooledConnection(
                id=str(uuid.uuid4()),
                connection=raw_conn
            )

            self._connections[conn.id] = conn
            self._idle.append(conn.id)

            self._stats.total_connections_created += 1
            self._stats.current_size = len(self._connections)
            self._stats.idle_count = len(self._idle)

            logger.debug(f"Connection created: {conn.id}")

            return conn

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

    async def _create_connection_async(self) -> Optional[PooledConnection[T]]:
        """Create connection asynchronously."""
        if len(self._connections) >= self.config.max_size:
            return None

        try:
            raw_conn = await asyncio.to_thread(self._factory)

            conn = PooledConnection(
                id=str(uuid.uuid4()),
                connection=raw_conn
            )

            self._connections[conn.id] = conn
            self._idle.append(conn.id)

            self._stats.total_connections_created += 1
            self._stats.current_size = len(self._connections)
            self._stats.idle_count = len(self._idle)

            return conn

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

    def _close_connection(self, conn: PooledConnection[T]) -> None:
        """Close a connection."""
        try:
            if self._cleanup:
                self._cleanup(conn.connection)

            conn.state = ConnectionState.CLOSED

            if conn.id in self._connections:
                del self._connections[conn.id]

            self._stats.total_connections_closed += 1
            self._stats.current_size = len(self._connections)

            logger.debug(f"Connection closed: {conn.id}")

        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    async def _close_connection_async(
        self,
        conn: PooledConnection[T]
    ) -> None:
        """Close connection asynchronously."""
        try:
            if self._cleanup:
                await asyncio.to_thread(self._cleanup, conn.connection)

            conn.state = ConnectionState.CLOSED

            if conn.id in self._connections:
                del self._connections[conn.id]

            self._stats.total_connections_closed += 1
            self._stats.current_size = len(self._connections)

        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    # ========================================================================
    # ACQUIRE/RELEASE
    # ========================================================================

    def acquire(self, timeout: Optional[float] = None) -> Optional[T]:
        """
        Acquire a connection from the pool.

        Args:
            timeout: Maximum time to wait

        Returns:
            Connection or None if timeout
        """
        timeout = timeout or self.config.acquire_timeout_seconds
        deadline = time.time() + timeout

        with self._lock:
            while True:
                if self._state != PoolState.RUNNING:
                    return None

                # Try to get idle connection
                conn = self._select_connection()

                if conn:
                    conn.state = ConnectionState.IN_USE
                    conn.use_count += 1
                    conn.last_used = time.time()

                    self._stats.total_acquires += 1
                    self._stats.in_use_count += 1
                    self._stats.idle_count = len(self._idle)

                    return conn.connection

                # Try to create new connection
                if len(self._connections) < self.config.max_size:
                    new_conn = self._create_connection()
                    if new_conn:
                        continue

                # Wait for release
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._stats.timeouts += 1
                    self._stats.failed_acquires += 1
                    return None

                self._condition.wait(timeout=remaining)

    async def acquire_async(
        self,
        timeout: Optional[float] = None
    ) -> Optional[T]:
        """Acquire connection asynchronously."""
        timeout = timeout or self.config.acquire_timeout_seconds
        deadline = time.time() + timeout

        async with self._async_lock:
            while True:
                if self._state != PoolState.RUNNING:
                    return None

                # Try to get idle connection
                conn = self._select_connection()

                if conn:
                    conn.state = ConnectionState.IN_USE
                    conn.use_count += 1
                    conn.last_used = time.time()

                    self._stats.total_acquires += 1
                    self._stats.in_use_count += 1
                    self._stats.idle_count = len(self._idle)

                    return conn.connection

                # Try to create new connection
                if len(self._connections) < self.config.max_size:
                    new_conn = await self._create_connection_async()
                    if new_conn:
                        continue

                # Wait for release
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._stats.timeouts += 1
                    self._stats.failed_acquires += 1
                    return None

                try:
                    await asyncio.wait_for(
                        self._async_condition.wait(),
                        timeout=remaining
                    )
                except asyncio.TimeoutError:
                    pass

    def _select_connection(self) -> Optional[PooledConnection[T]]:
        """Select a connection based on strategy."""
        while self._idle:
            if self.config.selection_strategy == SelectionStrategy.FIFO:
                conn_id = self._idle.popleft()
            elif self.config.selection_strategy == SelectionStrategy.LIFO:
                conn_id = self._idle.pop()
            else:  # ROUND_ROBIN
                if not self._idle:
                    return None
                idx = self._rr_index % len(self._idle)
                conn_id = self._idle[idx]
                del self._idle[idx]
                self._rr_index += 1

            conn = self._connections.get(conn_id)

            if not conn:
                continue

            # Validate connection
            if not self._is_valid(conn):
                self._close_connection(conn)
                continue

            return conn

        return None

    def _is_valid(self, conn: PooledConnection[T]) -> bool:
        """Check if connection is valid."""
        # Check expiry
        if conn.is_expired(self.config.max_connection_age_seconds):
            return False

        # Check health
        if not conn.healthy:
            return False

        # Run validator if provided
        if self._validator:
            try:
                return self._validator(conn.connection)
            except Exception:
                return False

        return True

    def release(self, connection: T) -> None:
        """
        Release a connection back to the pool.

        Args:
            connection: The connection to release
        """
        with self._lock:
            # Find the pooled connection
            conn = None
            for c in self._connections.values():
                if c.connection is connection:
                    conn = c
                    break

            if not conn:
                logger.warning("Released unknown connection")
                return

            conn.state = ConnectionState.IDLE
            conn.last_used = time.time()

            self._idle.append(conn.id)

            self._stats.total_releases += 1
            self._stats.in_use_count -= 1
            self._stats.idle_count = len(self._idle)

            self._condition.notify()

    async def release_async(self, connection: T) -> None:
        """Release connection asynchronously."""
        async with self._async_lock:
            # Find the pooled connection
            conn = None
            for c in self._connections.values():
                if c.connection is connection:
                    conn = c
                    break

            if not conn:
                return

            conn.state = ConnectionState.IDLE
            conn.last_used = time.time()

            self._idle.append(conn.id)

            self._stats.total_releases += 1
            self._stats.in_use_count -= 1
            self._stats.idle_count = len(self._idle)

            self._async_condition.notify()

    # ========================================================================
    # CONTEXT MANAGERS
    # ========================================================================

    @contextmanager
    def connection(self):
        """Context manager for acquiring/releasing connection."""
        conn = self.acquire()
        if conn is None:
            raise RuntimeError("Failed to acquire connection")

        try:
            yield conn
        finally:
            self.release(conn)

    @asynccontextmanager
    async def connection_async(self):
        """Async context manager for connection."""
        conn = await self.acquire_async()
        if conn is None:
            raise RuntimeError("Failed to acquire connection")

        try:
            yield conn
        finally:
            await self.release_async(conn)

    # ========================================================================
    # MAINTENANCE
    # ========================================================================

    async def _maintenance_loop(self) -> None:
        """Background maintenance loop."""
        while self._state == PoolState.RUNNING:
            try:
                await self._perform_maintenance()
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

            await asyncio.sleep(self.config.validation_interval_seconds)

    async def _perform_maintenance(self) -> None:
        """Perform pool maintenance."""
        async with self._async_lock:
            # Close idle connections that have been idle too long
            now = time.time()
            to_close = []

            for conn_id in list(self._idle):
                conn = self._connections.get(conn_id)
                if not conn:
                    continue

                # Check idle time (keep minimum connections)
                if (len(self._connections) > self.config.min_size and
                    conn.is_idle_too_long(self.config.max_idle_time_seconds)):
                    to_close.append(conn)
                    self._idle.remove(conn_id)

                # Check age
                elif conn.is_expired(self.config.max_connection_age_seconds):
                    to_close.append(conn)
                    self._idle.remove(conn_id)

            for conn in to_close:
                await self._close_connection_async(conn)

            self._stats.idle_count = len(self._idle)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return self._stats.to_dict()

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._connections)

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return len(self._idle)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_pool(
    factory: Callable[[], Any],
    min_size: int = 1,
    max_size: int = 10,
    **kwargs
) -> ConnectionPool:
    """Create a connection pool."""
    config = PoolConfig(
        min_size=min_size,
        max_size=max_size,
        **kwargs
    )
    return ConnectionPool(factory, config)
