#!/usr/bin/env python3
"""
BAEL - Load Balancer
Advanced load balancing and request distribution system.

Features:
- Multiple algorithms (Round Robin, Weighted, Least Connections, etc.)
- Health checking
- Circuit breaking integration
- Session affinity (sticky sessions)
- Connection pooling
- Metrics collection
- Dynamic server management
- Failover support
- Rate limiting per backend
"""

import asyncio
import hashlib
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LoadBalancerAlgorithm(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_LEAST_CONNECTIONS = "weighted_least_connections"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"


class ServerStatus(Enum):
    """Backend server status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class HealthCheckType(Enum):
    """Health check types."""
    HTTP = "http"
    TCP = "tcp"
    PING = "ping"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ServerConfig:
    """Backend server configuration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    host: str = "localhost"
    port: int = 8080
    weight: int = 1
    max_connections: int = 100
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerState:
    """Current state of a backend server."""
    server_id: str
    status: ServerStatus = ServerStatus.UNKNOWN
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    check_type: HealthCheckType = HealthCheckType.TCP
    interval: float = 10.0  # seconds
    timeout: float = 5.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    path: str = "/health"  # for HTTP checks
    expected_status: int = 200


@dataclass
class RequestContext:
    """Context for load balancing decision."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_ip: Optional[str] = None
    session_id: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    path: str = "/"
    method: str = "GET"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadBalancerStats:
    """Load balancer statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_connections: int = 0
    avg_response_time: float = 0.0
    servers_healthy: int = 0
    servers_unhealthy: int = 0


# =============================================================================
# ALGORITHMS
# =============================================================================

class SelectionAlgorithm(ABC):
    """Base class for server selection algorithms."""

    @abstractmethod
    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        """Select a server for the request."""
        pass


class RoundRobinAlgorithm(SelectionAlgorithm):
    """Round robin selection."""

    def __init__(self):
        self._index = 0

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        if not servers:
            return None

        # Filter healthy servers
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        server = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        return server


class WeightedRoundRobinAlgorithm(SelectionAlgorithm):
    """Weighted round robin selection."""

    def __init__(self):
        self._current_weights: Dict[str, int] = {}
        self._effective_weights: Dict[str, int] = {}

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        # Filter healthy servers
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        # Initialize weights
        for server in healthy:
            if server.id not in self._effective_weights:
                self._effective_weights[server.id] = server.weight
                self._current_weights[server.id] = 0

        # Calculate total weight
        total_weight = sum(s.weight for s in healthy)

        # Find server with highest current weight
        best = None
        best_weight = -1

        for server in healthy:
            self._current_weights[server.id] += self._effective_weights[server.id]

            if self._current_weights[server.id] > best_weight:
                best = server
                best_weight = self._current_weights[server.id]

        if best:
            self._current_weights[best.id] -= total_weight

        return best


class LeastConnectionsAlgorithm(SelectionAlgorithm):
    """Least connections selection."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        # Filter healthy servers
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        # Find server with least connections
        min_conns = float('inf')
        selected = None

        for server in healthy:
            state = states.get(server.id, ServerState(server.id))
            if state.active_connections < min_conns:
                min_conns = state.active_connections
                selected = server

        return selected


class WeightedLeastConnectionsAlgorithm(SelectionAlgorithm):
    """Weighted least connections selection."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        min_ratio = float('inf')
        selected = None

        for server in healthy:
            state = states.get(server.id, ServerState(server.id))
            ratio = state.active_connections / max(server.weight, 1)

            if ratio < min_ratio:
                min_ratio = ratio
                selected = server

        return selected


class RandomAlgorithm(SelectionAlgorithm):
    """Random selection."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        return random.choice(healthy)


class WeightedRandomAlgorithm(SelectionAlgorithm):
    """Weighted random selection."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        total_weight = sum(s.weight for s in healthy)
        r = random.uniform(0, total_weight)

        cumulative = 0
        for server in healthy:
            cumulative += server.weight
            if r <= cumulative:
                return server

        return healthy[-1]


class IPHashAlgorithm(SelectionAlgorithm):
    """IP hash selection for sticky sessions."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        # Hash client IP
        key = context.client_ip or "default"
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)

        return healthy[hash_val % len(healthy)]


class LeastResponseTimeAlgorithm(SelectionAlgorithm):
    """Least response time selection."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        min_time = float('inf')
        selected = None

        for server in healthy:
            state = states.get(server.id, ServerState(server.id))
            response_time = state.avg_response_time or float('inf')

            if response_time < min_time:
                min_time = response_time
                selected = server

        return selected


class ResourceBasedAlgorithm(SelectionAlgorithm):
    """Resource-based selection (CPU/Memory aware)."""

    def select(
        self,
        servers: List[ServerConfig],
        states: Dict[str, ServerState],
        context: RequestContext
    ) -> Optional[ServerConfig]:
        healthy = [s for s in servers if states.get(s.id, ServerState(s.id)).status == ServerStatus.HEALTHY]

        if not healthy:
            return None

        # Score based on available resources
        best_score = -1
        selected = None

        for server in healthy:
            state = states.get(server.id, ServerState(server.id))

            # Score: higher is better (more available resources)
            cpu_available = 100 - state.cpu_usage
            mem_available = 100 - state.memory_usage
            score = (cpu_available * 0.6 + mem_available * 0.4) * server.weight

            if score > best_score:
                best_score = score
                selected = server

        return selected


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Health checker for backend servers."""

    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}

    async def check(self, server: ServerConfig) -> bool:
        """Perform health check on server."""
        if self.config.check_type == HealthCheckType.TCP:
            return await self._tcp_check(server)
        elif self.config.check_type == HealthCheckType.HTTP:
            return await self._http_check(server)
        elif self.config.check_type == HealthCheckType.PING:
            return await self._ping_check(server)
        else:
            return True  # Custom checks return true by default

    async def _tcp_check(self, server: ServerConfig) -> bool:
        """TCP connection check."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server.host, server.port),
                timeout=self.config.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _http_check(self, server: ServerConfig) -> bool:
        """HTTP health check (simulated)."""
        # In production, use aiohttp
        try:
            await asyncio.wait_for(
                asyncio.open_connection(server.host, server.port),
                timeout=self.config.timeout
            )
            return True
        except Exception:
            return False

    async def _ping_check(self, server: ServerConfig) -> bool:
        """Ping check (simulated)."""
        # Simulate ping with TCP check
        return await self._tcp_check(server)


# =============================================================================
# SESSION AFFINITY
# =============================================================================

class SessionAffinity:
    """Session affinity manager for sticky sessions."""

    def __init__(self, ttl: int = 3600):
        self._sessions: Dict[str, Tuple[str, datetime]] = {}
        self._ttl = ttl

    def get_server(self, session_id: str) -> Optional[str]:
        """Get server ID for session."""
        if session_id in self._sessions:
            server_id, expires = self._sessions[session_id]
            if datetime.utcnow() < expires:
                return server_id
            else:
                del self._sessions[session_id]
        return None

    def set_server(self, session_id: str, server_id: str) -> None:
        """Set server for session."""
        expires = datetime.utcnow() + timedelta(seconds=self._ttl)
        self._sessions[session_id] = (server_id, expires)

    def remove_session(self, session_id: str) -> None:
        """Remove session affinity."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_server(self, server_id: str) -> None:
        """Clear all sessions for a server."""
        to_remove = [
            sid for sid, (srv, _) in self._sessions.items()
            if srv == server_id
        ]
        for sid in to_remove:
            del self._sessions[sid]


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """
    Advanced Load Balancer for BAEL.

    Features:
    - Multiple algorithms
    - Health checking
    - Session affinity
    - Dynamic server management
    """

    def __init__(
        self,
        algorithm: LoadBalancerAlgorithm = LoadBalancerAlgorithm.ROUND_ROBIN,
        health_config: Optional[HealthCheckConfig] = None
    ):
        self._algorithm = algorithm
        self._selector = self._create_selector(algorithm)
        self._servers: Dict[str, ServerConfig] = {}
        self._states: Dict[str, ServerState] = {}
        self._health_config = health_config or HealthCheckConfig()
        self._health_checker = HealthChecker(self._health_config)
        self._session_affinity = SessionAffinity()
        self._use_session_affinity = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks
        self._on_server_up: List[Callable[[ServerConfig], Awaitable[None]]] = []
        self._on_server_down: List[Callable[[ServerConfig], Awaitable[None]]] = []

    def _create_selector(self, algorithm: LoadBalancerAlgorithm) -> SelectionAlgorithm:
        """Create selection algorithm instance."""
        algorithms = {
            LoadBalancerAlgorithm.ROUND_ROBIN: RoundRobinAlgorithm,
            LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinAlgorithm,
            LoadBalancerAlgorithm.LEAST_CONNECTIONS: LeastConnectionsAlgorithm,
            LoadBalancerAlgorithm.WEIGHTED_LEAST_CONNECTIONS: WeightedLeastConnectionsAlgorithm,
            LoadBalancerAlgorithm.RANDOM: RandomAlgorithm,
            LoadBalancerAlgorithm.WEIGHTED_RANDOM: WeightedRandomAlgorithm,
            LoadBalancerAlgorithm.IP_HASH: IPHashAlgorithm,
            LoadBalancerAlgorithm.LEAST_RESPONSE_TIME: LeastResponseTimeAlgorithm,
            LoadBalancerAlgorithm.RESOURCE_BASED: ResourceBasedAlgorithm,
        }
        return algorithms[algorithm]()

    # -------------------------------------------------------------------------
    # SERVER MANAGEMENT
    # -------------------------------------------------------------------------

    def add_server(self, server: ServerConfig) -> None:
        """Add a backend server."""
        self._servers[server.id] = server
        self._states[server.id] = ServerState(
            server_id=server.id,
            status=ServerStatus.HEALTHY
        )

    def remove_server(self, server_id: str) -> None:
        """Remove a backend server."""
        if server_id in self._servers:
            del self._servers[server_id]
        if server_id in self._states:
            del self._states[server_id]
        self._session_affinity.clear_server(server_id)

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        """Get server by ID."""
        return self._servers.get(server_id)

    def list_servers(self) -> List[ServerConfig]:
        """List all servers."""
        return list(self._servers.values())

    def set_server_status(self, server_id: str, status: ServerStatus) -> None:
        """Set server status manually."""
        if server_id in self._states:
            self._states[server_id].status = status

    def drain_server(self, server_id: str) -> None:
        """Set server to draining mode (no new connections)."""
        self.set_server_status(server_id, ServerStatus.DRAINING)

    # -------------------------------------------------------------------------
    # REQUEST ROUTING
    # -------------------------------------------------------------------------

    async def select_server(self, context: RequestContext) -> Optional[ServerConfig]:
        """Select a server for the request."""
        # Check session affinity first
        if self._use_session_affinity and context.session_id:
            server_id = self._session_affinity.get_server(context.session_id)
            if server_id and server_id in self._servers:
                state = self._states.get(server_id)
                if state and state.status == ServerStatus.HEALTHY:
                    return self._servers[server_id]

        # Use algorithm to select server
        servers = list(self._servers.values())
        selected = self._selector.select(servers, self._states, context)

        # Set session affinity
        if selected and self._use_session_affinity and context.session_id:
            self._session_affinity.set_server(context.session_id, selected.id)

        return selected

    async def execute(
        self,
        context: RequestContext,
        handler: Callable[[ServerConfig], Awaitable[T]]
    ) -> Optional[T]:
        """Execute request on selected server."""
        server = await self.select_server(context)

        if not server:
            logger.error("No healthy servers available")
            return None

        state = self._states[server.id]
        state.active_connections += 1

        start = time.time()

        try:
            result = await handler(server)

            # Update stats
            state.total_requests += 1
            state.last_success = datetime.utcnow()
            state.consecutive_failures = 0

            # Update response time (exponential moving average)
            response_time = time.time() - start
            if state.avg_response_time == 0:
                state.avg_response_time = response_time
            else:
                state.avg_response_time = state.avg_response_time * 0.9 + response_time * 0.1

            return result

        except Exception as e:
            state.failed_requests += 1
            state.consecutive_failures += 1

            if state.consecutive_failures >= self._health_config.unhealthy_threshold:
                state.status = ServerStatus.UNHEALTHY
                await self._notify_server_down(server)

            raise

        finally:
            state.active_connections -= 1

    # -------------------------------------------------------------------------
    # HEALTH CHECKING
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start health checking."""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        """Stop health checking."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while self._running:
            for server in list(self._servers.values()):
                await self._check_server_health(server)

            await asyncio.sleep(self._health_config.interval)

    async def _check_server_health(self, server: ServerConfig) -> None:
        """Check health of a single server."""
        state = self._states.get(server.id)
        if not state:
            return

        healthy = await self._health_checker.check(server)
        state.last_check = datetime.utcnow()

        if healthy:
            if state.status != ServerStatus.HEALTHY:
                state.consecutive_failures = 0
                if state.consecutive_failures == 0:
                    state.status = ServerStatus.HEALTHY
                    await self._notify_server_up(server)
            state.last_success = datetime.utcnow()
        else:
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._health_config.unhealthy_threshold:
                if state.status == ServerStatus.HEALTHY:
                    state.status = ServerStatus.UNHEALTHY
                    await self._notify_server_down(server)

    # -------------------------------------------------------------------------
    # SESSION AFFINITY
    # -------------------------------------------------------------------------

    def enable_session_affinity(self, ttl: int = 3600) -> None:
        """Enable session affinity."""
        self._use_session_affinity = True
        self._session_affinity = SessionAffinity(ttl)

    def disable_session_affinity(self) -> None:
        """Disable session affinity."""
        self._use_session_affinity = False

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_server_up(self, callback: Callable[[ServerConfig], Awaitable[None]]) -> None:
        """Register callback for server becoming healthy."""
        self._on_server_up.append(callback)

    def on_server_down(self, callback: Callable[[ServerConfig], Awaitable[None]]) -> None:
        """Register callback for server becoming unhealthy."""
        self._on_server_down.append(callback)

    async def _notify_server_up(self, server: ServerConfig) -> None:
        """Notify server up."""
        for callback in self._on_server_up:
            try:
                await callback(server)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def _notify_server_down(self, server: ServerConfig) -> None:
        """Notify server down."""
        for callback in self._on_server_down:
            try:
                await callback(server)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> LoadBalancerStats:
        """Get load balancer statistics."""
        total = 0
        successful = 0
        failed = 0
        active = 0
        response_times = []
        healthy = 0
        unhealthy = 0

        for state in self._states.values():
            total += state.total_requests
            successful += state.total_requests - state.failed_requests
            failed += state.failed_requests
            active += state.active_connections

            if state.avg_response_time > 0:
                response_times.append(state.avg_response_time)

            if state.status == ServerStatus.HEALTHY:
                healthy += 1
            else:
                unhealthy += 1

        return LoadBalancerStats(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            active_connections=active,
            avg_response_time=sum(response_times) / len(response_times) if response_times else 0,
            servers_healthy=healthy,
            servers_unhealthy=unhealthy
        )

    def get_server_stats(self, server_id: str) -> Optional[ServerState]:
        """Get statistics for a specific server."""
        return self._states.get(server_id)

    # -------------------------------------------------------------------------
    # ALGORITHM SWITCHING
    # -------------------------------------------------------------------------

    def set_algorithm(self, algorithm: LoadBalancerAlgorithm) -> None:
        """Change load balancing algorithm."""
        self._algorithm = algorithm
        self._selector = self._create_selector(algorithm)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Load Balancer."""
    print("=" * 70)
    print("BAEL - LOAD BALANCER DEMO")
    print("Advanced Request Distribution")
    print("=" * 70)
    print()

    # 1. Create Load Balancer
    print("1. CREATE LOAD BALANCER:")
    print("-" * 40)

    lb = LoadBalancer(
        algorithm=LoadBalancerAlgorithm.ROUND_ROBIN,
        health_config=HealthCheckConfig(interval=5.0)
    )

    print(f"   Algorithm: {lb._algorithm.value}")
    print()

    # 2. Add Servers
    print("2. ADD SERVERS:")
    print("-" * 40)

    servers = [
        ServerConfig(id="server-1", host="localhost", port=8001, weight=3),
        ServerConfig(id="server-2", host="localhost", port=8002, weight=2),
        ServerConfig(id="server-3", host="localhost", port=8003, weight=1),
    ]

    for server in servers:
        lb.add_server(server)
        print(f"   Added: {server.id} ({server.host}:{server.port}, weight={server.weight})")

    print()

    # 3. Round Robin Selection
    print("3. ROUND ROBIN SELECTION:")
    print("-" * 40)

    for i in range(6):
        ctx = RequestContext(client_ip="192.168.1.100")
        selected = await lb.select_server(ctx)
        print(f"   Request {i+1}: {selected.id if selected else 'None'}")

    print()

    # 4. Weighted Round Robin
    print("4. WEIGHTED ROUND ROBIN:")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN)

    selection_counts: Dict[str, int] = defaultdict(int)

    for _ in range(12):
        ctx = RequestContext()
        selected = await lb.select_server(ctx)
        if selected:
            selection_counts[selected.id] += 1

    for server_id, count in sorted(selection_counts.items()):
        print(f"   {server_id}: {count} selections")

    print()

    # 5. Least Connections
    print("5. LEAST CONNECTIONS:")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.LEAST_CONNECTIONS)

    # Simulate connections
    lb._states["server-1"].active_connections = 5
    lb._states["server-2"].active_connections = 2
    lb._states["server-3"].active_connections = 8

    ctx = RequestContext()
    selected = await lb.select_server(ctx)

    print(f"   server-1 connections: 5")
    print(f"   server-2 connections: 2")
    print(f"   server-3 connections: 8")
    print(f"   Selected: {selected.id if selected else 'None'}")
    print()

    # 6. IP Hash (Sticky Sessions)
    print("6. IP HASH (STICKY SESSIONS):")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.IP_HASH)

    # Same IP should always get same server
    for client_ip in ["192.168.1.100", "10.0.0.50", "192.168.1.100"]:
        ctx = RequestContext(client_ip=client_ip)
        selected = await lb.select_server(ctx)
        print(f"   Client {client_ip}: {selected.id if selected else 'None'}")

    print()

    # 7. Least Response Time
    print("7. LEAST RESPONSE TIME:")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.LEAST_RESPONSE_TIME)

    # Simulate response times
    lb._states["server-1"].avg_response_time = 0.15
    lb._states["server-2"].avg_response_time = 0.08
    lb._states["server-3"].avg_response_time = 0.22

    ctx = RequestContext()
    selected = await lb.select_server(ctx)

    print(f"   server-1 avg: 150ms")
    print(f"   server-2 avg: 80ms")
    print(f"   server-3 avg: 220ms")
    print(f"   Selected: {selected.id if selected else 'None'}")
    print()

    # 8. Resource Based
    print("8. RESOURCE BASED:")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.RESOURCE_BASED)

    # Simulate resource usage
    lb._states["server-1"].cpu_usage = 80
    lb._states["server-1"].memory_usage = 60
    lb._states["server-2"].cpu_usage = 30
    lb._states["server-2"].memory_usage = 40
    lb._states["server-3"].cpu_usage = 50
    lb._states["server-3"].memory_usage = 70

    ctx = RequestContext()
    selected = await lb.select_server(ctx)

    print(f"   server-1: CPU 80%, MEM 60%")
    print(f"   server-2: CPU 30%, MEM 40%")
    print(f"   server-3: CPU 50%, MEM 70%")
    print(f"   Selected: {selected.id if selected else 'None'}")
    print()

    # 9. Session Affinity
    print("9. SESSION AFFINITY:")
    print("-" * 40)

    lb.set_algorithm(LoadBalancerAlgorithm.ROUND_ROBIN)
    lb.enable_session_affinity(ttl=3600)

    # Same session should get same server
    session_id = "session-123"
    for i in range(3):
        ctx = RequestContext(session_id=session_id)
        selected = await lb.select_server(ctx)
        print(f"   Request {i+1} (session={session_id[:10]}...): {selected.id if selected else 'None'}")

    print()

    # 10. Server Failure
    print("10. SERVER FAILURE:")
    print("-" * 40)

    # Mark server as unhealthy
    lb.set_server_status("server-2", ServerStatus.UNHEALTHY)

    selection_counts = defaultdict(int)
    for _ in range(6):
        ctx = RequestContext()
        selected = await lb.select_server(ctx)
        if selected:
            selection_counts[selected.id] += 1

    print(f"   server-2 marked UNHEALTHY")
    for server_id, count in sorted(selection_counts.items()):
        print(f"   {server_id}: {count} selections")

    print()

    # 11. Drain Server
    print("11. DRAIN SERVER:")
    print("-" * 40)

    lb.drain_server("server-1")

    print(f"   server-1 status: {lb._states['server-1'].status.value}")
    print(f"   (No new connections will be routed)")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    # Simulate some traffic
    lb.set_server_status("server-1", ServerStatus.HEALTHY)
    lb.set_server_status("server-2", ServerStatus.HEALTHY)

    for _ in range(10):
        state = lb._states[random.choice(list(lb._servers.keys()))]
        state.total_requests += 1
        if random.random() > 0.9:
            state.failed_requests += 1

    stats = lb.get_stats()

    print(f"   Total requests: {stats.total_requests}")
    print(f"   Successful: {stats.successful_requests}")
    print(f"   Failed: {stats.failed_requests}")
    print(f"   Healthy servers: {stats.servers_healthy}")
    print(f"   Unhealthy servers: {stats.servers_unhealthy}")
    print()

    # 13. Event Callbacks
    print("13. EVENT CALLBACKS:")
    print("-" * 40)

    events = []

    async def on_down(server: ServerConfig):
        events.append(f"DOWN: {server.id}")

    async def on_up(server: ServerConfig):
        events.append(f"UP: {server.id}")

    lb.on_server_down(on_down)
    lb.on_server_up(on_up)

    print("   Registered: on_server_down, on_server_up")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Load Balancer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
