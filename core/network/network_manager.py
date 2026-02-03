#!/usr/bin/env python3
"""
BAEL - Network Manager
Advanced network operations and monitoring for AI agents.

Features:
- HTTP/HTTPS client with retry logic
- WebSocket support
- Connection pooling
- DNS resolution
- Network health monitoring
- Bandwidth management
- Latency tracking
- Protocol handlers
- SSL/TLS management
- Proxy support
"""

import asyncio
import hashlib
import json
import logging
import socket
import ssl
import struct
import time
import urllib.parse
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class Protocol(Enum):
    """Network protocols."""
    HTTP = "http"
    HTTPS = "https"
    WS = "ws"
    WSS = "wss"
    TCP = "tcp"
    UDP = "udp"


class ConnectionState(Enum):
    """Connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class NetworkConfig:
    """Network configuration."""
    timeout: float = 30.0
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    max_connections: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    verify_ssl: bool = True
    proxy: Optional[str] = None


@dataclass
class HttpRequest:
    """HTTP request definition."""
    url: str
    method: HttpMethod = HttpMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    params: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[float] = None


@dataclass
class HttpResponse:
    """HTTP response."""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    elapsed: float = 0.0

    @property
    def text(self) -> str:
        return self.body.decode('utf-8', errors='replace')

    @property
    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class ConnectionInfo:
    """Connection information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    host: str = ""
    port: int = 80
    protocol: Protocol = Protocol.HTTP
    state: ConnectionState = ConnectionState.DISCONNECTED
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    bytes_sent: int = 0
    bytes_received: int = 0
    request_count: int = 0


@dataclass
class LatencyStats:
    """Latency statistics."""
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    samples: int = 0


@dataclass
class BandwidthStats:
    """Bandwidth statistics."""
    bytes_sent: int = 0
    bytes_received: int = 0
    send_rate: float = 0.0  # bytes/sec
    receive_rate: float = 0.0  # bytes/sec
    period_seconds: float = 0.0


@dataclass
class HealthCheck:
    """Health check result."""
    target: str
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DnsResult:
    """DNS resolution result."""
    hostname: str
    addresses: List[str] = field(default_factory=list)
    canonical_name: Optional[str] = None
    ttl: int = 0
    resolved_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# URL PARSER
# =============================================================================

class URLParser:
    """Parse and manipulate URLs."""

    @staticmethod
    def parse(url: str) -> Dict[str, Any]:
        """Parse URL into components."""
        parsed = urllib.parse.urlparse(url)

        # Parse query string
        query = dict(urllib.parse.parse_qsl(parsed.query))

        # Determine port
        port = parsed.port
        if port is None:
            if parsed.scheme == 'https':
                port = 443
            elif parsed.scheme == 'http':
                port = 80
            else:
                port = 80

        return {
            'scheme': parsed.scheme,
            'host': parsed.hostname or '',
            'port': port,
            'path': parsed.path or '/',
            'query': query,
            'fragment': parsed.fragment
        }

    @staticmethod
    def build(
        scheme: str,
        host: str,
        port: Optional[int] = None,
        path: str = '/',
        query: Optional[Dict[str, str]] = None,
        fragment: Optional[str] = None
    ) -> str:
        """Build URL from components."""
        # Add port if non-standard
        netloc = host
        if port:
            if not ((scheme == 'http' and port == 80) or (scheme == 'https' and port == 443)):
                netloc = f"{host}:{port}"

        # Build query string
        qs = urllib.parse.urlencode(query) if query else ''

        return urllib.parse.urlunparse((
            scheme,
            netloc,
            path,
            '',
            qs,
            fragment or ''
        ))

    @staticmethod
    def join(base: str, path: str) -> str:
        """Join base URL with path."""
        return urllib.parse.urljoin(base, path)


# =============================================================================
# DNS RESOLVER
# =============================================================================

class DnsResolver:
    """DNS resolution with caching."""

    def __init__(self, cache_ttl: int = 300):
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, DnsResult] = {}

    async def resolve(self, hostname: str, use_cache: bool = True) -> DnsResult:
        """Resolve hostname to IP addresses."""
        # Check cache
        if use_cache and hostname in self._cache:
            cached = self._cache[hostname]
            age = (datetime.utcnow() - cached.resolved_at).total_seconds()
            if age < self.cache_ttl:
                return cached

        try:
            # Perform DNS lookup
            loop = asyncio.get_event_loop()
            addrs = await loop.run_in_executor(
                None,
                lambda: socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            )

            # Extract unique addresses
            addresses = list(set(addr[4][0] for addr in addrs))

            result = DnsResult(
                hostname=hostname,
                addresses=addresses,
                ttl=self.cache_ttl
            )

            # Cache result
            self._cache[hostname] = result

            return result

        except socket.gaierror as e:
            return DnsResult(
                hostname=hostname,
                addresses=[],
                ttl=0
            )

    def clear_cache(self) -> int:
        """Clear DNS cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# LATENCY TRACKER
# =============================================================================

class LatencyTracker:
    """Track and analyze latency."""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._samples: List[float] = []

    def record(self, latency_ms: float) -> None:
        """Record a latency sample."""
        self._samples.append(latency_ms)

        # Trim if needed
        if len(self._samples) > self.max_samples:
            self._samples = self._samples[-self.max_samples:]

    def get_stats(self) -> LatencyStats:
        """Calculate latency statistics."""
        if not self._samples:
            return LatencyStats()

        sorted_samples = sorted(self._samples)
        n = len(sorted_samples)

        return LatencyStats(
            min_ms=sorted_samples[0],
            max_ms=sorted_samples[-1],
            avg_ms=sum(sorted_samples) / n,
            p50_ms=sorted_samples[int(n * 0.5)],
            p95_ms=sorted_samples[int(n * 0.95)] if n > 20 else sorted_samples[-1],
            p99_ms=sorted_samples[int(n * 0.99)] if n > 100 else sorted_samples[-1],
            samples=n
        )

    def clear(self) -> None:
        """Clear samples."""
        self._samples.clear()


# =============================================================================
# BANDWIDTH MONITOR
# =============================================================================

class BandwidthMonitor:
    """Monitor bandwidth usage."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._sent: List[Tuple[float, int]] = []
        self._received: List[Tuple[float, int]] = []

    def record_sent(self, bytes_count: int) -> None:
        """Record bytes sent."""
        now = time.time()
        self._sent.append((now, bytes_count))
        self._cleanup()

    def record_received(self, bytes_count: int) -> None:
        """Record bytes received."""
        now = time.time()
        self._received.append((now, bytes_count))
        self._cleanup()

    def get_stats(self) -> BandwidthStats:
        """Get bandwidth statistics."""
        self._cleanup()

        now = time.time()
        cutoff = now - self.window_seconds

        sent = sum(b for t, b in self._sent if t > cutoff)
        received = sum(b for t, b in self._received if t > cutoff)

        return BandwidthStats(
            bytes_sent=sent,
            bytes_received=received,
            send_rate=sent / self.window_seconds,
            receive_rate=received / self.window_seconds,
            period_seconds=self.window_seconds
        )

    def _cleanup(self) -> None:
        """Remove old samples."""
        cutoff = time.time() - self.window_seconds * 2
        self._sent = [(t, b) for t, b in self._sent if t > cutoff]
        self._received = [(t, b) for t, b in self._received if t > cutoff]


# =============================================================================
# CONNECTION POOL
# =============================================================================

class ConnectionPool:
    """Pool of reusable connections."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._connections: Dict[str, List[ConnectionInfo]] = defaultdict(list)
        self._in_use: Set[str] = set()
        self._lock = asyncio.Lock()

    async def acquire(self, host: str, port: int, protocol: Protocol) -> ConnectionInfo:
        """Acquire a connection from the pool."""
        key = f"{protocol.value}://{host}:{port}"

        async with self._lock:
            # Check for existing connection
            pool = self._connections[key]

            for conn in pool:
                if conn.id not in self._in_use:
                    conn.last_used = datetime.utcnow()
                    self._in_use.add(conn.id)
                    return conn

            # Create new connection
            conn = ConnectionInfo(
                host=host,
                port=port,
                protocol=protocol,
                state=ConnectionState.CONNECTED
            )

            pool.append(conn)
            self._in_use.add(conn.id)

            return conn

    async def release(self, conn: ConnectionInfo) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            self._in_use.discard(conn.id)

    async def close(self, conn: ConnectionInfo) -> None:
        """Close and remove a connection."""
        async with self._lock:
            key = f"{conn.protocol.value}://{conn.host}:{conn.port}"
            self._in_use.discard(conn.id)

            pool = self._connections[key]
            self._connections[key] = [c for c in pool if c.id != conn.id]

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        total = sum(len(conns) for conns in self._connections.values())
        return {
            "total_connections": total,
            "in_use": len(self._in_use),
            "available": total - len(self._in_use),
            "pools": len(self._connections)
        }


# =============================================================================
# RETRY HANDLER
# =============================================================================

class RetryHandler:
    """Handle request retries."""

    def __init__(
        self,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt."""
        if self.strategy == RetryStrategy.NONE:
            return 0
        elif self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay * (2 ** (attempt - 1))

        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, error: Optional[Exception] = None) -> bool:
        """Check if should retry."""
        if self.strategy == RetryStrategy.NONE:
            return False
        return attempt < self.max_attempts

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute with retry."""
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if not self.should_retry(attempt):
                    raise

                delay = self.get_delay(attempt)
                logger.warning(f"Retry {attempt}/{self.max_attempts} after {delay}s: {e}")
                await asyncio.sleep(delay)

        if last_error:
            raise last_error


# =============================================================================
# HTTP CLIENT
# =============================================================================

class SimpleHttpClient:
    """Minimal HTTP client implementation."""

    def __init__(self, config: Optional[NetworkConfig] = None):
        self.config = config or NetworkConfig()

    async def request(self, req: HttpRequest) -> HttpResponse:
        """Send HTTP request."""
        start = time.time()

        # Parse URL
        parsed = URLParser.parse(req.url)
        host = parsed['host']
        port = parsed['port']
        path = parsed['path']

        # Add query params
        if req.params:
            query_str = urllib.parse.urlencode(req.params)
            path = f"{path}?{query_str}"

        # Determine if SSL
        use_ssl = parsed['scheme'] == 'https'

        try:
            # Open connection
            if use_ssl:
                ssl_ctx = ssl.create_default_context()
                if not self.config.verify_ssl:
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=ssl_ctx),
                    timeout=self.config.connect_timeout
                )
            else:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self.config.connect_timeout
                )

            try:
                # Build request
                request_lines = [f"{req.method.value} {path} HTTP/1.1"]

                # Add headers
                headers = {
                    'Host': host,
                    'Connection': 'close',
                    'User-Agent': 'BAEL-NetworkManager/1.0'
                }
                headers.update(req.headers)

                if req.body:
                    headers['Content-Length'] = str(len(req.body))

                for key, value in headers.items():
                    request_lines.append(f"{key}: {value}")

                request_lines.append('')
                request_lines.append('')

                request_data = '\r\n'.join(request_lines).encode('utf-8')
                if req.body:
                    request_data += req.body

                # Send request
                writer.write(request_data)
                await writer.drain()

                # Read response
                response_data = await asyncio.wait_for(
                    reader.read(65536),
                    timeout=req.timeout or self.config.read_timeout
                )

                # Parse response
                return self._parse_response(response_data, time.time() - start)

            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except:
                    pass

        except asyncio.TimeoutError:
            return HttpResponse(
                status_code=0,
                headers={'error': 'timeout'},
                elapsed=time.time() - start
            )
        except Exception as e:
            return HttpResponse(
                status_code=0,
                headers={'error': str(e)},
                elapsed=time.time() - start
            )

    def _parse_response(self, data: bytes, elapsed: float) -> HttpResponse:
        """Parse HTTP response."""
        try:
            # Split headers and body
            if b'\r\n\r\n' in data:
                header_data, body = data.split(b'\r\n\r\n', 1)
            else:
                header_data = data
                body = b''

            header_lines = header_data.decode('utf-8', errors='replace').split('\r\n')

            # Parse status line
            status_line = header_lines[0]
            parts = status_line.split(' ', 2)
            status_code = int(parts[1]) if len(parts) > 1 else 0

            # Parse headers
            headers = {}
            for line in header_lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            return HttpResponse(
                status_code=status_code,
                headers=headers,
                body=body,
                elapsed=elapsed
            )

        except Exception as e:
            return HttpResponse(
                status_code=0,
                headers={'error': str(e)},
                body=data,
                elapsed=elapsed
            )

    async def get(self, url: str, **kwargs) -> HttpResponse:
        """GET request."""
        return await self.request(HttpRequest(url=url, method=HttpMethod.GET, **kwargs))

    async def post(self, url: str, body: Optional[bytes] = None, **kwargs) -> HttpResponse:
        """POST request."""
        return await self.request(HttpRequest(url=url, method=HttpMethod.POST, body=body, **kwargs))

    async def put(self, url: str, body: Optional[bytes] = None, **kwargs) -> HttpResponse:
        """PUT request."""
        return await self.request(HttpRequest(url=url, method=HttpMethod.PUT, body=body, **kwargs))

    async def delete(self, url: str, **kwargs) -> HttpResponse:
        """DELETE request."""
        return await self.request(HttpRequest(url=url, method=HttpMethod.DELETE, **kwargs))


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Check health of network endpoints."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._http = SimpleHttpClient()

    async def check_tcp(self, host: str, port: int) -> HealthCheck:
        """Check TCP connectivity."""
        start = time.time()

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()

            return HealthCheck(
                target=f"{host}:{port}",
                status=HealthStatus.HEALTHY,
                latency_ms=(time.time() - start) * 1000
            )
        except asyncio.TimeoutError:
            return HealthCheck(
                target=f"{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                error="Connection timeout"
            )
        except Exception as e:
            return HealthCheck(
                target=f"{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def check_http(self, url: str, expected_status: int = 200) -> HealthCheck:
        """Check HTTP endpoint."""
        start = time.time()

        try:
            response = await self._http.get(url, timeout=self.timeout)

            if response.status_code == expected_status:
                status = HealthStatus.HEALTHY
            elif 200 <= response.status_code < 500:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheck(
                target=url,
                status=status,
                latency_ms=response.elapsed * 1000
            )
        except Exception as e:
            return HealthCheck(
                target=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def check_dns(self, hostname: str) -> HealthCheck:
        """Check DNS resolution."""
        start = time.time()
        resolver = DnsResolver()

        result = await resolver.resolve(hostname, use_cache=False)

        if result.addresses:
            return HealthCheck(
                target=hostname,
                status=HealthStatus.HEALTHY,
                latency_ms=(time.time() - start) * 1000
            )
        else:
            return HealthCheck(
                target=hostname,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start) * 1000,
                error="DNS resolution failed"
            )


# =============================================================================
# WEBSOCKET CLIENT
# =============================================================================

class WebSocketFrame:
    """WebSocket frame."""

    OPCODE_CONTINUATION = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xA

    def __init__(
        self,
        opcode: int,
        payload: bytes,
        fin: bool = True,
        masked: bool = True
    ):
        self.opcode = opcode
        self.payload = payload
        self.fin = fin
        self.masked = masked

    def encode(self) -> bytes:
        """Encode frame to bytes."""
        # First byte: FIN + opcode
        first_byte = (0x80 if self.fin else 0x00) | self.opcode

        # Second byte: MASK + length
        length = len(self.payload)

        if length <= 125:
            second_byte = (0x80 if self.masked else 0x00) | length
            header = bytes([first_byte, second_byte])
        elif length <= 65535:
            second_byte = (0x80 if self.masked else 0x00) | 126
            header = bytes([first_byte, second_byte]) + struct.pack('>H', length)
        else:
            second_byte = (0x80 if self.masked else 0x00) | 127
            header = bytes([first_byte, second_byte]) + struct.pack('>Q', length)

        if self.masked:
            import os
            mask_key = os.urandom(4)
            masked_payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(self.payload))
            return header + mask_key + masked_payload

        return header + self.payload


class SimpleWebSocket:
    """Simple WebSocket client."""

    def __init__(self):
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self, url: str) -> bool:
        """Connect to WebSocket server."""
        parsed = URLParser.parse(url)
        host = parsed['host']
        port = parsed['port']
        path = parsed['path'] or '/'
        use_ssl = parsed['scheme'] in ('wss', 'https')

        try:
            if use_ssl:
                ssl_ctx = ssl.create_default_context()
                self._reader, self._writer = await asyncio.open_connection(
                    host, port, ssl=ssl_ctx
                )
            else:
                self._reader, self._writer = await asyncio.open_connection(host, port)

            # Send handshake
            import base64
            import os
            key = base64.b64encode(os.urandom(16)).decode()

            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )

            self._writer.write(handshake.encode())
            await self._writer.drain()

            # Read response
            response = await self._reader.readline()
            if b'101' not in response:
                return False

            # Read headers until empty line
            while True:
                line = await self._reader.readline()
                if line == b'\r\n':
                    break

            self._connected = True
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def send(self, data: Union[str, bytes]) -> bool:
        """Send data."""
        if not self._connected or not self._writer:
            return False

        try:
            if isinstance(data, str):
                frame = WebSocketFrame(
                    opcode=WebSocketFrame.OPCODE_TEXT,
                    payload=data.encode()
                )
            else:
                frame = WebSocketFrame(
                    opcode=WebSocketFrame.OPCODE_BINARY,
                    payload=data
                )

            self._writer.write(frame.encode())
            await self._writer.drain()
            return True

        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
            return False

    async def recv(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive data."""
        if not self._connected or not self._reader:
            return None

        try:
            # Read first two bytes
            if timeout:
                header = await asyncio.wait_for(
                    self._reader.read(2),
                    timeout=timeout
                )
            else:
                header = await self._reader.read(2)

            if len(header) < 2:
                return None

            # Parse header
            opcode = header[0] & 0x0F
            masked = bool(header[1] & 0x80)
            length = header[1] & 0x7F

            # Extended length
            if length == 126:
                ext = await self._reader.read(2)
                length = struct.unpack('>H', ext)[0]
            elif length == 127:
                ext = await self._reader.read(8)
                length = struct.unpack('>Q', ext)[0]

            # Mask key
            if masked:
                mask_key = await self._reader.read(4)

            # Payload
            payload = await self._reader.read(length)

            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

            return payload

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"WebSocket recv failed: {e}")
            return None

    async def close(self) -> None:
        """Close connection."""
        if self._writer:
            try:
                # Send close frame
                frame = WebSocketFrame(
                    opcode=WebSocketFrame.OPCODE_CLOSE,
                    payload=b''
                )
                self._writer.write(frame.encode())
                await self._writer.drain()
                self._writer.close()
                await self._writer.wait_closed()
            except:
                pass

        self._connected = False


# =============================================================================
# NETWORK MANAGER
# =============================================================================

class NetworkManager:
    """
    Network Manager for BAEL.

    Comprehensive network operations and monitoring.
    """

    def __init__(self, config: Optional[NetworkConfig] = None):
        self.config = config or NetworkConfig()
        self._http = SimpleHttpClient(self.config)
        self._dns = DnsResolver()
        self._pool = ConnectionPool(self.config.max_connections)
        self._latency = LatencyTracker()
        self._bandwidth = BandwidthMonitor()
        self._health = HealthChecker(self.config.timeout)
        self._retry = RetryHandler(
            strategy=self.config.retry_strategy,
            max_attempts=self.config.retry_attempts,
            base_delay=self.config.retry_delay
        )

    # -------------------------------------------------------------------------
    # HTTP OPERATIONS
    # -------------------------------------------------------------------------

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> HttpResponse:
        """HTTP GET request."""
        async def _do_get():
            response = await self._http.get(url, headers=headers or {})
            self._track_request(response)
            return response

        return await self._retry.execute(_do_get)

    async def post(
        self,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HttpResponse:
        """HTTP POST request."""
        async def _do_post():
            response = await self._http.post(url, body=body, headers=headers or {})
            self._track_request(response, len(body) if body else 0)
            return response

        return await self._retry.execute(_do_post)

    async def put(
        self,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> HttpResponse:
        """HTTP PUT request."""
        async def _do_put():
            response = await self._http.put(url, body=body, headers=headers or {})
            self._track_request(response, len(body) if body else 0)
            return response

        return await self._retry.execute(_do_put)

    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> HttpResponse:
        """HTTP DELETE request."""
        async def _do_delete():
            response = await self._http.delete(url, headers=headers or {})
            self._track_request(response)
            return response

        return await self._retry.execute(_do_delete)

    async def request(self, req: HttpRequest) -> HttpResponse:
        """Generic HTTP request."""
        async def _do_request():
            response = await self._http.request(req)
            self._track_request(response, len(req.body) if req.body else 0)
            return response

        return await self._retry.execute(_do_request)

    def _track_request(self, response: HttpResponse, sent_bytes: int = 0) -> None:
        """Track request metrics."""
        self._latency.record(response.elapsed * 1000)
        self._bandwidth.record_sent(sent_bytes)
        self._bandwidth.record_received(len(response.body))

    # -------------------------------------------------------------------------
    # DNS
    # -------------------------------------------------------------------------

    async def resolve(self, hostname: str) -> DnsResult:
        """Resolve DNS."""
        return await self._dns.resolve(hostname)

    def clear_dns_cache(self) -> int:
        """Clear DNS cache."""
        return self._dns.clear_cache()

    # -------------------------------------------------------------------------
    # HEALTH CHECKS
    # -------------------------------------------------------------------------

    async def check_health(self, target: str) -> HealthCheck:
        """Check health of target."""
        if target.startswith('http'):
            return await self._health.check_http(target)
        elif ':' in target:
            host, port = target.rsplit(':', 1)
            return await self._health.check_tcp(host, int(port))
        else:
            return await self._health.check_dns(target)

    async def check_all(self, targets: List[str]) -> List[HealthCheck]:
        """Check health of multiple targets."""
        tasks = [self.check_health(target) for target in targets]
        return await asyncio.gather(*tasks)

    # -------------------------------------------------------------------------
    # WEBSOCKET
    # -------------------------------------------------------------------------

    async def websocket_connect(self, url: str) -> SimpleWebSocket:
        """Connect to WebSocket."""
        ws = SimpleWebSocket()
        await ws.connect(url)
        return ws

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_latency_stats(self) -> LatencyStats:
        """Get latency statistics."""
        return self._latency.get_stats()

    def get_bandwidth_stats(self) -> BandwidthStats:
        """Get bandwidth statistics."""
        return self._bandwidth.get_stats()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self._pool.get_stats()

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all network statistics."""
        return {
            "latency": self.get_latency_stats().__dict__,
            "bandwidth": self.get_bandwidth_stats().__dict__,
            "pool": self.get_pool_stats()
        }

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def parse_url(self, url: str) -> Dict[str, Any]:
        """Parse URL into components."""
        return URLParser.parse(url)

    def build_url(self, **kwargs) -> str:
        """Build URL from components."""
        return URLParser.build(**kwargs)

    def join_url(self, base: str, path: str) -> str:
        """Join URL with path."""
        return URLParser.join(base, path)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Network Manager."""
    print("=" * 70)
    print("BAEL - NETWORK MANAGER DEMO")
    print("Advanced Network Operations for AI Agents")
    print("=" * 70)
    print()

    network = NetworkManager(NetworkConfig(
        timeout=10.0,
        retry_attempts=2,
        retry_strategy=RetryStrategy.EXPONENTIAL
    ))

    # 1. URL Parsing
    print("1. URL PARSING:")
    print("-" * 40)

    url = "https://example.com:443/path/to/resource?key=value&foo=bar#section"
    parsed = network.parse_url(url)
    print(f"   URL: {url}")
    print(f"   Scheme: {parsed['scheme']}")
    print(f"   Host: {parsed['host']}")
    print(f"   Port: {parsed['port']}")
    print(f"   Path: {parsed['path']}")
    print(f"   Query: {parsed['query']}")
    print()

    # 2. URL Building
    print("2. URL BUILDING:")
    print("-" * 40)

    built = network.build_url(
        scheme="https",
        host="api.example.com",
        path="/v1/users",
        query={"page": "1", "limit": "10"}
    )
    print(f"   Built URL: {built}")
    print()

    # 3. DNS Resolution
    print("3. DNS RESOLUTION:")
    print("-" * 40)

    hostname = "example.com"
    result = await network.resolve(hostname)
    print(f"   Hostname: {result.hostname}")
    print(f"   Addresses: {result.addresses[:3]}")
    print()

    # 4. Health Checks
    print("4. HEALTH CHECKS:")
    print("-" * 40)

    # DNS health check
    dns_health = await network.check_health("example.com")
    print(f"   DNS Check: {dns_health.target}")
    print(f"   Status: {dns_health.status.value}")
    print(f"   Latency: {dns_health.latency_ms:.2f}ms")
    print()

    # 5. Latency Tracking
    print("5. LATENCY TRACKING:")
    print("-" * 40)

    # Simulate some latency samples
    for ms in [10, 15, 12, 18, 11, 25, 14, 13, 16, 20]:
        network._latency.record(ms)

    stats = network.get_latency_stats()
    print(f"   Samples: {stats.samples}")
    print(f"   Min: {stats.min_ms:.2f}ms")
    print(f"   Max: {stats.max_ms:.2f}ms")
    print(f"   Avg: {stats.avg_ms:.2f}ms")
    print(f"   P50: {stats.p50_ms:.2f}ms")
    print(f"   P95: {stats.p95_ms:.2f}ms")
    print()

    # 6. Bandwidth Monitoring
    print("6. BANDWIDTH MONITORING:")
    print("-" * 40)

    # Simulate bandwidth
    for _ in range(5):
        network._bandwidth.record_sent(1024)
        network._bandwidth.record_received(4096)

    bw = network.get_bandwidth_stats()
    print(f"   Bytes Sent: {bw.bytes_sent}")
    print(f"   Bytes Received: {bw.bytes_received}")
    print(f"   Send Rate: {bw.send_rate:.2f} B/s")
    print(f"   Receive Rate: {bw.receive_rate:.2f} B/s")
    print()

    # 7. Connection Pool
    print("7. CONNECTION POOL:")
    print("-" * 40)

    pool_stats = network.get_pool_stats()
    print(f"   Total Connections: {pool_stats['total_connections']}")
    print(f"   In Use: {pool_stats['in_use']}")
    print(f"   Available: {pool_stats['available']}")
    print()

    # 8. Retry Handler
    print("8. RETRY HANDLER:")
    print("-" * 40)

    retry = RetryHandler(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=3,
        base_delay=1.0
    )

    for attempt in range(1, 4):
        delay = retry.get_delay(attempt)
        should = retry.should_retry(attempt)
        print(f"   Attempt {attempt}: delay={delay:.2f}s, should_retry={should}")
    print()

    # 9. HTTP Methods (simulated)
    print("9. HTTP CLIENT METHODS:")
    print("-" * 40)

    print("   Supported methods:")
    for method in HttpMethod:
        print(f"   - {method.value}")
    print()

    # 10. All Stats
    print("10. ALL STATISTICS:")
    print("-" * 40)

    all_stats = network.get_all_stats()
    print(f"   Latency avg: {all_stats['latency']['avg_ms']:.2f}ms")
    print(f"   Bandwidth sent: {all_stats['bandwidth']['bytes_sent']} bytes")
    print(f"   Pool connections: {all_stats['pool']['total_connections']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Network Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
