"""
BAEL API Gateway - Enterprise-grade request routing, load balancing, and caching

Features:
- Intelligent request routing
- Load balancing across backend instances
- Multi-layer caching (memory + Redis)
- Per-tenant rate limiting
- Circuit breaker pattern
- Request/response transformation
- API versioning support
- Metrics and monitoring
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Load balancing strategy"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    IP_HASH = "ip_hash"
    RANDOM = "random"


class CircuitState(str, Enum):
    """Circuit breaker state"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class Backend:
    """Backend service instance"""
    id: str
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0

    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    ttl_seconds: int
    hit_count: int = 0

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class MemoryCache:
    """In-memory LRU cache"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: deque = deque()

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        entry = self.cache.get(key)

        if entry and not entry.is_expired():
            entry.hit_count += 1

            # Update LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

            return entry.value

        # Expired or not found
        if entry:
            del self.cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cached value"""
        # Evict if needed
        if len(self.cache) >= self.max_size:
            # Remove oldest
            if self.access_order:
                oldest_key = self.access_order.popleft()
                del self.cache[oldest_key]

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl,
        )

        self.cache[key] = entry
        self.access_order.append(key)

    async def delete(self, key: str):
        """Delete cached value"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)

    async def clear(self):
        """Clear all cached values"""
        self.cache.clear()
        self.access_order.clear()

    def stats(self) -> Dict:
        """Get cache statistics"""
        total_hits = sum(e.hit_count for e in self.cache.values())

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'total_hits': total_hits,
            'utilization': len(self.cache) / self.max_size * 100,
        }


class RateLimiter:
    """Token bucket rate limiter per tenant"""

    def __init__(self):
        self.buckets: Dict[str, Dict[str, Any]] = {}

    async def check_limit(
        self,
        tenant_id: str,
        config: RateLimitConfig
    ) -> bool:
        """Check if request is within rate limit"""
        now = time.time()

        if tenant_id not in self.buckets:
            self.buckets[tenant_id] = {
                'tokens': config.requests_per_minute,
                'last_update': now,
                'requests_minute': deque(),
                'requests_hour': deque(),
            }

        bucket = self.buckets[tenant_id]

        # Refill tokens based on time passed
        time_passed = now - bucket['last_update']
        refill = time_passed * (config.requests_per_minute / 60.0)
        bucket['tokens'] = min(
            config.requests_per_minute + config.burst_size,
            bucket['tokens'] + refill
        )
        bucket['last_update'] = now

        # Clean old requests
        minute_ago = now - 60
        hour_ago = now - 3600

        bucket['requests_minute'] = deque([
            t for t in bucket['requests_minute']
            if t > minute_ago
        ])
        bucket['requests_hour'] = deque([
            t for t in bucket['requests_hour']
            if t > hour_ago
        ])

        # Check limits
        if len(bucket['requests_minute']) >= config.requests_per_minute:
            return False

        if len(bucket['requests_hour']) >= config.requests_per_hour:
            return False

        if bucket['tokens'] < 1:
            return False

        # Allow request
        bucket['tokens'] -= 1
        bucket['requests_minute'].append(now)
        bucket['requests_hour'].append(now)

        return True

    def get_stats(self, tenant_id: str) -> Dict:
        """Get rate limit stats for tenant"""
        if tenant_id not in self.buckets:
            return {}

        bucket = self.buckets[tenant_id]

        return {
            'tokens_available': int(bucket['tokens']),
            'requests_last_minute': len(bucket['requests_minute']),
            'requests_last_hour': len(bucket['requests_hour']),
        }


class CircuitBreaker:
    """Circuit breaker for backend health"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    async def call(self, backend_id: str, func: Callable) -> Any:
        """Execute function with circuit breaker"""
        if self.state == CircuitState.OPEN:
            # Check if we should try to recover
            if self.last_failure_time:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker for {backend_id} entering half-open state")
                else:
                    raise Exception(f"Circuit breaker open for {backend_id}")

        try:
            result = await func()

            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker for {backend_id} closed")

            return result

        except Exception as e:
            # Failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker for {backend_id} opened after {self.failure_count} failures")

            raise e


class LoadBalancer:
    """Load balancer for routing requests"""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.backends: List[Backend] = []
        self.current_index = 0
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

    def add_backend(self, backend: Backend):
        """Add backend instance"""
        self.backends.append(backend)
        self.circuit_breakers[backend.id] = CircuitBreaker()
        logger.info(f"Added backend: {backend.url()}")

    def remove_backend(self, backend_id: str):
        """Remove backend instance"""
        self.backends = [b for b in self.backends if b.id != backend_id]
        if backend_id in self.circuit_breakers:
            del self.circuit_breakers[backend_id]
        logger.info(f"Removed backend: {backend_id}")

    async def select_backend(self, client_ip: Optional[str] = None) -> Optional[Backend]:
        """Select backend using configured strategy"""
        healthy_backends = [b for b in self.backends if b.healthy]

        if not healthy_backends:
            return None

        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            backend = healthy_backends[self.current_index % len(healthy_backends)]
            self.current_index += 1
            return backend

        elif self.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return min(healthy_backends, key=lambda b: b.connections)

        elif self.strategy == RoutingStrategy.WEIGHTED:
            # Weighted random selection
            total_weight = sum(b.weight for b in healthy_backends)
            import random
            r = random.randint(0, total_weight - 1)
            cumulative = 0
            for backend in healthy_backends:
                cumulative += backend.weight
                if r < cumulative:
                    return backend
            return healthy_backends[-1]

        elif self.strategy == RoutingStrategy.IP_HASH:
            if client_ip:
                hash_val = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
                return healthy_backends[hash_val % len(healthy_backends)]
            return healthy_backends[0]

        else:  # RANDOM
            import random
            return random.choice(healthy_backends)

    def get_stats(self) -> Dict:
        """Get load balancer statistics"""
        return {
            'total_backends': len(self.backends),
            'healthy_backends': len([b for b in self.backends if b.healthy]),
            'strategy': self.strategy.value,
            'backends': [
                {
                    'id': b.id,
                    'url': b.url(),
                    'healthy': b.healthy,
                    'connections': b.connections,
                    'total_requests': b.total_requests,
                    'failed_requests': b.failed_requests,
                    'avg_response_time_ms': b.avg_response_time_ms,
                }
                for b in self.backends
            ],
        }


class APIGateway:
    """API Gateway for BAEL"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_cache: bool = True,
        enable_rate_limit: bool = True,
    ):
        self.enable_cache = enable_cache
        self.enable_rate_limit = enable_rate_limit

        # Components
        self.load_balancer = LoadBalancer(RoutingStrategy.ROUND_ROBIN)
        self.memory_cache = MemoryCache(max_size=10000)
        self.rate_limiter = RateLimiter()

        # Redis cache (optional)
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

        # Metrics
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limited = 0

        # Default rate limit config
        self.default_rate_limit = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10,
        )

    async def start(self):
        """Start gateway"""
        if self.redis_url and REDIS_AVAILABLE:
            self.redis = await redis.from_url(self.redis_url)
            logger.info("Redis cache enabled")

        logger.info("API Gateway started")

    async def stop(self):
        """Stop gateway"""
        if self.redis:
            await self.redis.close()

        logger.info("API Gateway stopped")

    async def handle_request(
        self,
        method: str,
        path: str,
        tenant_id: str,
        client_ip: str,
        body: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict:
        """Handle incoming request"""
        self.total_requests += 1
        start_time = time.time()

        # Rate limiting
        if self.enable_rate_limit:
            allowed = await self.rate_limiter.check_limit(
                tenant_id,
                self.default_rate_limit
            )

            if not allowed:
                self.rate_limited += 1
                return {
                    'status': 429,
                    'error': 'Rate limit exceeded',
                    'retry_after': 60,
                }

        # Check cache for GET requests
        if self.enable_cache and method == 'GET':
            cache_key = self._generate_cache_key(path, tenant_id)
            cached = await self._get_from_cache(cache_key)

            if cached:
                self.cache_hits += 1
                return {
                    'status': 200,
                    'data': cached,
                    'cached': True,
                    'duration_ms': (time.time() - start_time) * 1000,
                }
            else:
                self.cache_misses += 1

        # Select backend
        backend = await self.load_balancer.select_backend(client_ip)
        if not backend:
            return {
                'status': 503,
                'error': 'No healthy backends available',
            }

        # Forward request to backend
        try:
            backend.connections += 1
            backend.total_requests += 1

            # Simulate backend call (replace with actual HTTP request)
            response = await self._call_backend(backend, method, path, body, headers)

            # Cache successful GET responses
            if self.enable_cache and method == 'GET' and response.get('status') == 200:
                cache_key = self._generate_cache_key(path, tenant_id)
                await self._set_in_cache(cache_key, response['data'])

            duration_ms = (time.time() - start_time) * 1000
            backend.avg_response_time_ms = (
                (backend.avg_response_time_ms * (backend.total_requests - 1) + duration_ms)
                / backend.total_requests
            )

            response['duration_ms'] = duration_ms
            return response

        except Exception as e:
            backend.failed_requests += 1
            logger.error(f"Backend request failed: {e}")

            return {
                'status': 500,
                'error': str(e),
            }

        finally:
            backend.connections -= 1

    async def _call_backend(
        self,
        backend: Backend,
        method: str,
        path: str,
        body: Optional[Dict],
        headers: Optional[Dict],
    ) -> Dict:
        """Call backend service (mock implementation)"""
        # In production, use aiohttp or httpx to make actual HTTP requests
        await asyncio.sleep(0.01)  # Simulate network delay

        return {
            'status': 200,
            'data': {'message': 'Success', 'backend': backend.id},
        }

    def _generate_cache_key(self, path: str, tenant_id: str) -> str:
        """Generate cache key"""
        return f"{tenant_id}:{path}"

    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get from cache (memory + Redis)"""
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value:
            return value

        # Try Redis cache
        if self.redis:
            value = await self.redis.get(key)
            if value:
                # Populate memory cache
                import json
                parsed = json.loads(value)
                await self.memory_cache.set(key, parsed, ttl=300)
                return parsed

        return None

    async def _set_in_cache(self, key: str, value: Any, ttl: int = 300):
        """Set in cache (memory + Redis)"""
        # Set in memory cache
        await self.memory_cache.set(key, value, ttl)

        # Set in Redis cache
        if self.redis:
            import json
            await self.redis.setex(key, ttl, json.dumps(value))

    def get_stats(self) -> Dict:
        """Get gateway statistics"""
        cache_hit_rate = (
            (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return {
            'total_requests': self.total_requests,
            'cache': {
                'enabled': self.enable_cache,
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'hit_rate': round(cache_hit_rate, 2),
                **self.memory_cache.stats(),
            },
            'rate_limiting': {
                'enabled': self.enable_rate_limit,
                'requests_blocked': self.rate_limited,
            },
            'load_balancer': self.load_balancer.get_stats(),
        }
